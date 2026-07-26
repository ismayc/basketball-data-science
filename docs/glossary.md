# Glossary

Every term of art used across the portfolio's analyses, defined once.
Maintained by `tools/glossary.py`, which also stamps a per-document Terms
block at the top of each analysis and wraps each use in a hover tooltip
(`--sync` to update, `--check` gates staleness in the family runner).

| Term | Definition |
|---|---|
| **PPS** | Points per shot: total points on field-goal attempts divided by attempts. Free throws excluded. |
| **xPPS** | Expected points per shot - the model's fair price of a shot diet: what an average shooter would score on the same attempts, judged from location and shot type alone, before knowing what went in. |
| **xPTS** | Expected points: the modeled make probability times the shot's point value, summed over attempts. |
| **xMake** | The model's probability that a given shot goes in, estimated from location and shot type; the per-shot building block behind xPPS and xPTS. |
| **shot-making** | Actual minus expected points per 100 shots: conversion above or below what the shot diet itself explains. Positive means making shots the model prices as hard. |
| **EB making** | A player's shot-making after empirical-Bayes shrinkage: the observed number pulled toward the league mean in proportion to its sampling noise. The number to trust for projection. |
| **FGA** | Field-goal attempts. |
| **eFG%** | Effective field-goal percentage: field-goal percentage with made threes counted 1.5x, putting twos and threes on one points scale. |
| **RAPM** | Regularized adjusted plus-minus: a ridge regression crediting each player with net points per 100 possessions while adjusting for the other nine players on the floor. |
| **stint** | A stretch of game time with no substitution at either end - the unit of observation for the stint-level RAPM model. |
| **net_100** | Net points per 100 possessions: 100 x plus-minus / possessions; sits on the same scale as the NBA's published net rating. |
| **POSS** | Possession count in NBA lineup data - specifically offensive possessions for the lineup in question. |
| **plus-minus** | Points scored minus points allowed while a player or lineup is on the floor. |
| **2-for-1** | Shooting early with 25-36 seconds left in a period so your team gets two possessions to the opponent's one before the buzzer. |
| **rush** | Shots in the final four seconds of a period - the desperation window where both shot selection and execution collapse. |
| **decile calibration** | Split shots into ten bins by predicted make probability and compare predicted vs actual rates per bin; the reported number is the worst bin's gap. |
| **IRLS** | Iteratively reweighted least squares - the standard algorithm for fitting a logistic regression. |
| **ridge** | Ridge regression: least squares with an L2 penalty that keeps many-parameter models stable at the cost of a little bias. |
| **empirical Bayes** | Estimate the spread of true skill across the league from the data, then pull each individual's noisy estimate toward the league mean in proportion to its noise. |
| **shrinkage weight** | The fraction of an observed number that survives empirical-Bayes regression: 1 means fully trusted, 0 means replaced by the league mean. |
| **tau** | The estimated spread of true, noise-free skill across players (per 100 shots here); the knob that sets how hard empirical Bayes shrinks. |
| **MAE** | Mean absolute error. |
| **RMSE** | Root mean squared error. |
| **AUC** | Area under the ROC curve: the probability the model ranks a random positive case above a random negative one. 0.5 is a coin flip. |
| **log loss** | Negative average log-likelihood of the outcomes under the predicted probabilities; punishes confident wrong predictions. |
| **CI** | Confidence interval. |
| **Spearman** | Rank correlation: correlation of the orderings rather than the raw values. |
| **corner three** | A three-pointer from the corner, where the NBA line is roughly 3 ft closer than the arc - the geometry discount that makes it the cheapest three. |
| **SportVU** | The NBA's 2013-16 optical tracking system: x,y for all ten players (plus z for the ball) at 25 frames per second. |
| **window function** | SQL construct computing a value over a set of rows related to the current row (a rank, running total, or centered average) without collapsing them. |
| **DuckDB** | An in-process analytical SQL engine that queries CSV and parquet files directly, with no server or load step. |
| **HCA** | Home-court advantage, expressed here as net points per 100 possessions. |
