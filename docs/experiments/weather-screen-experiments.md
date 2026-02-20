# Weather Screen Experiments (Branch Notes)

Branch: `weather-screen-experiments`
Status: Paused / parked for later review.

## What We Tried
- Iterated Weather 1 typography/layout for low-res readability:
  - moved METAR line into first weather data row
  - removed `Temp` / `Humid` labels after testing to reduce clutter
  - set Weather 1 values to white for better contrast
- Tuned runway wind-speed label anchor behavior:
  - moved anchor to wind-arrow shaft midpoint
  - added runway-overlap detection and opposite-side fallback for wind-speed label placement

## Outcome
- Weather 1 readability improved with fewer labels.
- Runway view remains sensitive to information density (runway number + wind speed can be visually ambiguous at 64x64).
- Team decision: park this branch and continue from `main` for now.

## If We Resume This Branch
- Re-evaluate runway view numeric overlays:
  - either keep diagram-only runway view, or
  - time-multiplex numbers rather than drawing two numeric annotations at once
- Validate wind label placement on real device in multiple wind/runway alignments.
