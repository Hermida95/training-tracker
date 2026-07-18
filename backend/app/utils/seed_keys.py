"""Keys estables de los hábitos sembrados por app.seed.seed_data.

Se usan desde app.utils.stats (media de pasos) y desde los tests, así que
viven en su propio módulo para evitar import cycles con seed_data.py.
"""

STEPS_KEY = "steps"
WATER_KEY = "water"
MCGILL_KEY = "mcgill_big3"
HIP_MOBILITY_KEY = "hip_mobility"
SUNDAY_WALK_KEY = "sunday_walk"
