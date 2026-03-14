"""Seed global exercises (owner_id IS NULL) if the exercises table is empty."""
from sqlalchemy.orm import Session
from app.models import Exercise


GLOBAL_EXERCISES = [
    # Chest
    ("Barbell Bench Press", None, "chest", "barbell"),
    ("Dumbbell Bench Press", None, "chest", "dumbbell"),
    ("Incline Barbell Bench Press", None, "chest", "barbell"),
    ("Incline Dumbbell Press", None, "chest", "dumbbell"),
    ("Cable Fly", None, "chest", "cable"),
    ("Push-Up", None, "chest", "bodyweight"),
    # Back
    ("Pull-Up", None, "back", "bodyweight"),
    ("Barbell Row", None, "back", "barbell"),
    ("Dumbbell Row", None, "back", "dumbbell"),
    ("Lat Pulldown", None, "back", "machine"),
    ("Seated Cable Row", None, "back", "cable"),
    ("Face Pull", None, "back", "cable"),
    # Shoulders
    ("Overhead Press", None, "shoulders", "barbell"),
    ("Dumbbell Lateral Raise", None, "shoulders", "dumbbell"),
    ("Dumbbell Front Raise", None, "shoulders", "dumbbell"),
    ("Arnold Press", None, "shoulders", "dumbbell"),
    # Biceps
    ("Barbell Curl", None, "biceps", "barbell"),
    ("Dumbbell Curl", None, "biceps", "dumbbell"),
    ("Hammer Curl", None, "biceps", "dumbbell"),
    ("Preacher Curl", None, "biceps", "barbell"),
    # Triceps
    ("Tricep Pushdown", None, "triceps", "cable"),
    ("Skull Crusher", None, "triceps", "barbell"),
    ("Dips", None, "triceps", "bodyweight"),
    ("Overhead Tricep Extension", None, "triceps", "dumbbell"),
    # Abs
    ("Crunch", None, "abs", "bodyweight"),
    ("Plank", None, "abs", "bodyweight"),
    ("Leg Raise", None, "abs", "bodyweight"),
    ("Russian Twist", None, "abs", "bodyweight"),
    ("Cable Crunch", None, "abs", "cable"),
    # Glutes
    ("Hip Thrust", None, "glutes", "barbell"),
    ("Glute Bridge", None, "glutes", "bodyweight"),
    ("Cable Kickback", None, "glutes", "cable"),
    # Quads
    ("Barbell Squat", None, "quads", "barbell"),
    ("Leg Press", None, "quads", "machine"),
    ("Leg Extension", None, "quads", "machine"),
    ("Hack Squat", None, "quads", "machine"),
    ("Bulgarian Split Squat", None, "quads", "dumbbell"),
    # Hamstrings
    ("Romanian Deadlift", None, "hamstrings", "barbell"),
    ("Leg Curl", None, "hamstrings", "machine"),
    ("Good Morning", None, "hamstrings", "barbell"),
    # Calves
    ("Standing Calf Raise", None, "calves", "machine"),
    ("Seated Calf Raise", None, "calves", "machine"),
    # Full body
    ("Deadlift", None, "full_body", "barbell"),
    ("Power Clean", None, "full_body", "barbell"),
    ("Burpee", None, "full_body", "bodyweight"),
    ("Kettlebell Swing", None, "full_body", "kettlebell"),
    # Cardio
    ("Running", None, "cardio", "other"),
    ("Cycling", None, "cardio", "other"),
    ("Jump Rope", None, "cardio", "bodyweight"),
    ("Rowing Machine", None, "cardio", "machine"),
]


def seed_global_exercises(db: Session) -> None:
    """Insert global exercises (owner_id=NULL) only if the exercises table is empty."""
    if db.query(Exercise).limit(1).first() is not None:
        return
    for name, description, muscle_group, equipment in GLOBAL_EXERCISES:
        db.add(
            Exercise(
                name=name,
                description=description,
                muscle_group=muscle_group,
                equipment=equipment,
                owner_id=None,
            )
        )
    db.commit()
