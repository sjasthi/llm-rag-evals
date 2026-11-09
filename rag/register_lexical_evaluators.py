"""Register Token F1 and ROUGE-L v1.1 without modifying Gold Standard data."""

import json

from database import database_connection
from evaluator_catalog import definition_for
from settings import load_settings


EVALUATOR_KEYS = ("token_f1", "rouge_l")
EXPECTED_VERSION = "1.1"


def main() -> None:
    definitions = [definition_for(key) for key in EVALUATOR_KEYS]

    for definition in definitions:
        if definition["version"] != EXPECTED_VERSION:
            raise ValueError(
                f"{definition['key']} has unexpected version "
                f"{definition['version']!r}"
            )

    settings = load_settings()

    with database_connection(settings) as connection:
        try:
            connection.start_transaction()

            with connection.cursor() as cursor:
                for definition in definitions:
                    cursor.execute(
                        """
                        INSERT INTO evaluator_definitions
                        (
                            evaluator_key,
                            display_name,
                            family,
                            dimension,
                            version,
                            description,
                            configuration_json,
                            is_local,
                            is_deterministic
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            display_name = VALUES(display_name),
                            family = VALUES(family),
                            dimension = VALUES(dimension),
                            description = VALUES(description),
                            configuration_json = VALUES(configuration_json),
                            is_local = VALUES(is_local),
                            is_deterministic = VALUES(is_deterministic),
                            is_active = TRUE
                        """,
                        (
                            definition["key"],
                            definition["name"],
                            definition["family"],
                            definition["dimension"],
                            definition["version"],
                            definition["description"],
                            json.dumps(definition["configuration"]),
                            definition["is_local"],
                            definition["is_deterministic"],
                        ),
                    )

            connection.commit()

            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT
                        evaluator_id,
                        evaluator_key,
                        display_name,
                        version,
                        is_active
                    FROM evaluator_definitions
                    WHERE evaluator_key IN (%s, %s)
                      AND version = %s
                    ORDER BY evaluator_key
                    """,
                    (*EVALUATOR_KEYS, EXPECTED_VERSION),
                )
                registered = cursor.fetchall()

            if len(registered) != len(EVALUATOR_KEYS):
                raise RuntimeError(
                    "Not all lexical evaluator definitions were registered."
                )

            print(json.dumps(registered, indent=2, default=str))
            print("PASS: Both lexical evaluators registered as v1.1.")

        except Exception:
            connection.rollback()
            raise


if __name__ == "__main__":
    main()
