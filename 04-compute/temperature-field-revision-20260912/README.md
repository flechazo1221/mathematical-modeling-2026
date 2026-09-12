# Internal temperature-field revision

This isolated candidate revision changes the Q2--Q4 computation so that the
internal temperature field is advanced with the existing implicit backward-
Euler finite-volume conduction solver. The approved `04-compute/src` source,
approved results, H2/H3 decisions, and publication figures are not modified.

The revision does not add a latent-heat source. The latent-heat parameters are
not frozen in the approved model contract, so `latent_heat_source` is recorded
as `omitted_by_design`; this is a temperature-field correction, not the
claimed "with latent heat" model.

The Q3 full run reached the spatial and `dt=30 s` checks before the optional
`dt=15 s` run was stopped because of runtime. The Q4 representative run is
recorded in `results/q4-temperature-field-nr140.json`.
