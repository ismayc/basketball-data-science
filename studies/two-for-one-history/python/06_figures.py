"""Figures from the committed output tables (PNG + interactive HTML).

  figures/fig1_adoption.{png,html}  quick share at the decision mark vs the
                                    placebo mark, every season, both leagues
  figures/fig2_hazard.{png,html}    per-second first-act hazard ratio
                                    (decision / placebo) by era
  figures/fig3_payoff.{png,html}    quick minus not-quick net points, 95% CI

Run: python python/06_figures.py
"""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
import polars as pl
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
OUT, FIG = ROOT / "output", ROOT / "figures"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BLUE, ORANGE = "#2a78d6", "#eb6834"
# one-hue sequential ramp (light -> dark) for ordered eras
ERA_RAMP = ["#9ec5f4", "#5b9be6", "#2a78d6", "#1a4f99"]
LEAGUES = ["NBA", "WNBA"]


def style(fig: go.Figure, title: str, height: int) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=17, color=INK), x=0.01),
        paper_bgcolor=SURF, plot_bgcolor=SURF, height=height, width=1000,
        font=dict(family="Inter, Helvetica, Arial, sans-serif", color=INK2, size=13),
        margin=dict(l=60, r=30, t=80, b=150), hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.2, x=0.01))
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    return fig


def save(fig: go.Figure, name: str) -> None:
    FIG.mkdir(exist_ok=True)
    fig.write_html(FIG / f"{name}.html", include_plotlyjs="cdn")
    fig.write_image(FIG / f"{name}.png", scale=2)


def fig_adoption() -> None:
    a = pl.read_csv(OUT / "adoption_by_season.csv")
    fig = make_subplots(rows=1, cols=2, subplot_titles=LEAGUES, horizontal_spacing=0.08,
                        shared_yaxes=True)
    for i, lg in enumerate(LEAGUES, 1):
        d = a.filter(pl.col("league") == lg).sort("year")
        for col, name, color, dash in (("quick_share", "At the 2-for-1 mark", BLUE, "solid"),
                                       ("placebo_quick_share", "Placebo mark (2 min earlier)",
                                        ORANGE, "dot")):
            fig.add_trace(go.Scatter(
                x=d["year"], y=d[col], name=name, legendgroup=name, showlegend=i == 1,
                mode="lines+markers", line=dict(color=color, width=2, dash=dash),
                marker=dict(size=8, line=dict(color=SURF, width=2)),
                customdata=d["season"], hovertemplate="%{customdata}: %{y:.1%}"), 1, i)
    fig.update_yaxes(tickformat=".0%", range=[0.6, 1.0])
    fig.add_annotation(text="WNBA 2026 is a partial season; WNBA 1997-2005 used a 30 s clock and halves",
                       xref="paper", yref="paper", x=1, y=-0.42, showarrow=False,
                       font=dict(size=11, color=INK2), xanchor="right")
    save(style(fig, "Share of ball-holders who act early enough to get the ball back", 470),
         "fig1_adoption")


def fig_hazard() -> None:
    h = pl.read_csv(OUT / "hazard_by_era.csv")
    fig = make_subplots(rows=1, cols=2, subplot_titles=LEAGUES, horizontal_spacing=0.08,
                        shared_yaxes=True)
    for i, lg in enumerate(LEAGUES, 1):
        d = h.filter(pl.col("league") == lg)
        eras = sorted(d["era"].unique().to_list())
        ramp = ERA_RAMP[-len(eras):]
        for era, color in zip(eras, ramp):
            # 3-second centered rolling mean: single seconds are noisy in the WNBA
            e = (d.filter(pl.col("era") == era).sort("rel")
                 .with_columns(sm=pl.col("ratio").rolling_mean(3, center=True))
                 .filter(pl.col("rel").is_between(1, 20)))
            fig.add_trace(go.Scatter(
                x=e["rel"], y=e["sm"], name=f"{lg} {era}", mode="lines",
                line=dict(color=color, width=2),
                hovertemplate=f"{era}<br>%{{x}} s after mark: %{{y:.2f}}x"), 1, i)
        fig.add_vline(x=12, line=dict(color=INK2, width=1, dash="dash"), row=1, col=i)
    fig.add_hline(y=1, line=dict(color=INK2, width=1))
    fig.update_xaxes(title_text="Seconds after the mark")
    fig.update_yaxes(title_text="First-act rate vs placebo (3 s rolling)", row=1, col=1,
                     range=[0.7, 2.1])
    fig.add_annotation(text="Dashed line: the last second that still counts as a quick (2-for-1) release",
                       xref="paper", yref="paper", x=1, y=-0.62, showarrow=False,
                       font=dict(size=11, color=INK2), xanchor="right")
    save(style(fig, "How much faster teams shoot as the 2-for-1 deadline approaches", 600),
         "fig2_hazard")


def fig_payoff() -> None:
    p = pl.read_csv(OUT / "payoff_by_era.csv").sort("league", "era", descending=[True, True])
    labels = [f"{lg}  {e}" for lg, e in zip(p["league"], p["era"])]
    fig = go.Figure(go.Scatter(
        x=p["net_diff"], y=labels, mode="markers",
        marker=dict(size=10, color=BLUE, line=dict(color=SURF, width=2)),
        error_x=dict(type="data", symmetric=False, array=p["ci_hi"] - p["net_diff"],
                     arrayminus=p["net_diff"] - p["ci_lo"], color=BLUE, thickness=2, width=0),
        customdata=p.select("n_quick", "n_not").to_numpy(),
        hovertemplate="%{y}<br>+%{x:.2f} net pts<br>quick n=%{customdata[0]:,}, "
                      "not n=%{customdata[1]:,}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=INK2, width=1))
    fig.update_xaxes(title_text="Net points from the mark to the buzzer: quick minus not quick (95% bootstrap CI)")
    fig = style(fig, "The association is the same size in every era and both leagues", 440)
    fig.update_layout(margin=dict(b=70))
    save(fig,
         "fig3_payoff")


if __name__ == "__main__":
    fig_adoption()
    fig_hazard()
    fig_payoff()
    print("figures written")
