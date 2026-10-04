# Independent R/tidyverse implementation of python/02_decisions.py.
#
# Same specification (see the Python docstring), written separately so the
# reconcile gate (python/05_reconcile.py) can catch implementation bugs that
# a single pipeline would carry silently into every number.
#
# Input : data/raw/{nbastats,wnba_nbastats}_<yr>.parquet
# Output: output/decisions_r.parquet
#
# Run: Rscript R/02_decisions.R

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(stringr)
  library(nanoparquet)
})

args <- commandArgs(trailingOnly = FALSE)
script <- sub("--file=", "", args[grep("--file=", args)])
root <- normalizePath(file.path(dirname(script), ".."))
raw_dir <- file.path(root, "data", "raw")
out_dir <- file.path(root, "output")

PLACEBO_OFFSET <- 120

rules <- function(league, year) {
  if (league == "NBA") return(list(sc = 24, periods = 1:3))
  if (year <= 2005) return(list(sc = 30, periods = 1L))
  list(sc = 24, periods = 1:3)
}

side_of <- function(ptype) {
  case_when(ptype %in% c("4", "2") ~ "h",
            ptype %in% c("5", "3") ~ "v",
            TRUE ~ NA_character_)
}

prepare <- function(df) {
  df |>
    mutate(
      period = as.integer(PERIOD),
      eventnum = as.integer(EVENTNUM),
      t = as.numeric(str_split_i(PCTIMESTRING, ":", 1)) * 60 +
        as.numeric(str_split_i(PCTIMESTRING, ":", 2)),
      side = side_of(PERSON1TYPE),
      side3 = side_of(PERSON3TYPE),
      other = if_else(side == "h", "v", "h"),
      my_desc = coalesce(if_else(side == "h", HOMEDESCRIPTION, VISITORDESCRIPTION), ""),
      ft_miss = str_detect(my_desc, "MISS"),
      typ = EVENTMSGTYPE, act = EVENTMSGACTIONTYPE,
      last_ft = typ == "3" & act %in% c("10", "12", "15"),
      trip_ft = typ == "3" & act %in% c("10", "11", "12", "13", "14", "15"),
      offense_after = case_when(
        typ == "1" ~ other,
        typ == "2" ~ side,
        typ == "4" ~ side,
        typ == "5" ~ other,
        last_ft & !ft_miss ~ other,
        trip_ft ~ side,
        typ == "10" ~ side3,
        TRUE ~ NA_character_),
      pending = typ == "2" | (last_ft & ft_miss),
      owner_act = typ %in% c("1", "2", "5") |
        (typ == "3" & act %in% c("10", "11", "13")),
      v_score = suppressWarnings(as.integer(str_split_i(SCORE, " - ", 1))),
      h_score = suppressWarnings(as.integer(str_split_i(SCORE, " - ", 2)))
    ) |>
    arrange(GAME_ID, period, desc(t), eventnum) |>
    group_by(GAME_ID) |>
    fill(v_score, h_score, .direction = "down") |>
    mutate(v_score = coalesce(v_score, 0L), h_score = coalesce(h_score, 0L)) |>
    group_by(GAME_ID, period) |>
    mutate(
      own = offense_after,
      relevant = !is.na(offense_after)
    ) |>
    fill(own, .direction = "down") |>
    mutate(
      prev_own = lag(own),
      is_start = !is.na(own) & (is.na(prev_own) | own != prev_own),
      poss_id = cumsum(is_start),
      act_poss = poss_id - as.integer(is_start),
      start_t = if_else(is_start, t, NA_real_)
    ) |>
    fill(start_t, .direction = "down") |>
    mutate(act_start_t = if_else(is_start, lag(start_t), start_t)) |>
    ungroup()
}

team_map <- function(df) {
  df |>
    filter(PERSON1TYPE %in% c("4", "5"), !is.na(PLAYER1_TEAM_ID)) |>
    count(GAME_ID, PERSON1TYPE, PLAYER1_TEAM_ID, PLAYER1_TEAM_ABBREVIATION) |>
    group_by(GAME_ID, PERSON1TYPE) |>
    slice_max(n, n = 1, with_ties = FALSE) |>
    ungroup() |>
    mutate(side = if_else(PERSON1TYPE == "4", "h", "v")) |>
    select(GAME_ID, side, team_id = PLAYER1_TEAM_ID)
}

windows <- function(ev, T, periods) {
  ev <- filter(ev, period %in% periods)
  keys <- c("GAME_ID", "period")

  end <- ev |> group_by(GAME_ID, period) |>
    summarise(h_end = last(h_score), v_end = last(v_score), .groups = "drop")
  pre <- filter(ev, t > T)
  at_mark <- pre |> filter(relevant) |> group_by(GAME_ID, period) |>
    summarise(owner = last(offense_after), pending = last(pending), .groups = "drop")
  start_pre <- pre |> filter(is_start) |> group_by(GAME_ID, period) |>
    summarise(poss_start_t = last(t), .groups = "drop")
  score_mark <- pre |> group_by(GAME_ID, period) |>
    summarise(h_mark = last(h_score), v_mark = last(v_score), .groups = "drop")

  w <- end |> left_join(at_mark, by = keys) |> left_join(start_pre, by = keys) |>
    left_join(score_mark, by = keys)

  post <- ev |> filter(t <= T) |>
    inner_join(select(w, all_of(keys), owner), by = keys)
  first_act <- post |> filter(owner_act, side == owner) |>
    group_by(GAME_ID, period) |> summarise(first_act_t = first(t), .groups = "drop")
  later <- post |> filter(is_start, t > 0) |> group_by(GAME_ID, period) |>
    summarise(owner_later = sum(own == owner), opp_poss = sum(own != owner),
              last_poss = last(own), .groups = "drop")
  used <- post |>
    filter(owner_act, !is.na(prev_own), side == prev_own,
           coalesce(act_start_t, 9) > 1) |>
    group_by(GAME_ID, period) |>
    summarise(owner_used = n_distinct(act_poss[side == owner]),
              opp_used = n_distinct(act_poss[side != owner]),
              last_used = last(side), .groups = "drop")

  w |>
    left_join(first_act, by = keys) |>
    left_join(later, by = keys) |>
    left_join(used, by = keys) |>
    mutate(
      across(c(owner_later, opp_poss, owner_used, opp_used), ~ coalesce(as.integer(.x), 0L)),
      h_pts = h_end - coalesce(h_mark, h_end),
      v_pts = v_end - coalesce(v_mark, v_end),
      own_pts = if_else(owner == "h", h_pts, v_pts),
      opp_pts = if_else(owner == "h", v_pts, h_pts),
      net_pts = own_pts - opp_pts,
      got_last_used = coalesce(last_used, owner) == owner,
      choice = case_when(is.na(first_act_t) ~ "no_act",
                         first_act_t >= T - 12 ~ "quick",
                         first_act_t > T - 25 ~ "normal",
                         TRUE ~ "hold"),
      mark = T
    )
}

build <- function(league, year) {
  f <- file.path(raw_dir, sprintf("%snbastats_%d.parquet",
                                  if (league == "WNBA") "wnba_" else "", year))
  if (!file.exists(f)) return(NULL)
  r <- rules(league, year)
  T <- r$sc + 16
  ev <- prepare(read_parquet(f))
  teams <- team_map(ev)
  out <- bind_rows(
    windows(ev, T, r$periods) |> mutate(mark_kind = "decision"),
    windows(ev, T + PLACEBO_OFFSET, r$periods) |> mutate(mark_kind = "placebo")
  ) |>
    left_join(rename(teams, owner = side), by = c("GAME_ID", "owner")) |>
    mutate(league = league, year = as.integer(year))
  out
}

parts <- list()
for (league in c("NBA", "WNBA")) {
  years <- if (league == "NBA") 1996:2024 else 1997:2026
  for (y in years) {
    w <- build(league, y)
    if (is.null(w)) next
    ok <- filter(w, mark_kind == "decision", !is.na(owner), !pending)
    cat(sprintf("%s %d: %d windows, quick %.3f\n", league, y, nrow(w) / 2,
                mean(ok$choice == "quick")))
    parts[[length(parts) + 1]] <- w
  }
}
res <- bind_rows(parts) |>
  select(league, year, mark_kind, GAME_ID, period, mark, owner, pending, team_id,
         poss_start_t, first_act_t, choice, own_pts, opp_pts, net_pts,
         owner_used, opp_used, got_last_used, owner_later, opp_poss)
write_parquet(res, file.path(out_dir, "decisions_r.parquet"))
cat(sprintf("wrote %d windows\n", nrow(res)))
