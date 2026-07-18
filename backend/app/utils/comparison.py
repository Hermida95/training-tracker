from app.models.workout import WorkoutSession
from app.schemas.workout import ExerciseComparison, SessionComparison, SetComparison


def compare_sessions(current: WorkoutSession, previous: WorkoutSession | None) -> SessionComparison:
    """Compara serie a serie la sesión actual contra la anterior del mismo tipo.

    El emparejamiento es por nombre de ejercicio + número de serie: si el
    usuario cambió el orden o añadió un ejercicio nuevo, simplemente no habrá
    "previous" para esa serie (delta = None) en vez de romper.
    """
    previous_by_name: dict[str, dict[int, tuple[float | None, int | None]]] = {}
    if previous is not None:
        for exercise in previous.exercises:
            previous_by_name[exercise.name] = {
                s.set_number: (s.weight_kg, s.reps) for s in exercise.sets
            }

    exercise_comparisons = []
    for exercise in current.exercises:
        prev_sets = previous_by_name.get(exercise.name, {})
        set_comparisons = []
        for s in exercise.sets:
            prev_weight, prev_reps = prev_sets.get(s.set_number, (None, None))
            weight_delta = (
                round(s.weight_kg - prev_weight, 2)
                if s.weight_kg is not None and prev_weight is not None
                else None
            )
            reps_delta = (
                s.reps - prev_reps if s.reps is not None and prev_reps is not None else None
            )
            set_comparisons.append(
                SetComparison(
                    set_number=s.set_number,
                    previous_weight_kg=prev_weight,
                    previous_reps=prev_reps,
                    current_weight_kg=s.weight_kg,
                    current_reps=s.reps,
                    weight_delta_kg=weight_delta,
                    reps_delta=reps_delta,
                )
            )
        exercise_comparisons.append(ExerciseComparison(name=exercise.name, sets=set_comparisons))

    return SessionComparison(
        current_session_id=current.id,
        previous_session_id=previous.id if previous else None,
        previous_date=previous.date if previous else None,
        exercises=exercise_comparisons,
    )
