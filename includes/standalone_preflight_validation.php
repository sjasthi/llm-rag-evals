<?php
declare(strict_types=1);

/**
 * Validate a standalone citation-scoring preflight plan.
 *
 * This function performs no database operations,
 * Python execution, or external API calls.
 */
function validateStandalonePreflight(
    array $plan,
    array $allowedEvaluators,
    float $maxEstimatedCost = 0.25
): bool {
    $applications = $plan['applications'] ?? null;
    $paidCalls = $plan['paid_application_count'] ?? null;
    $unknownCostCalls = $plan['unknown_cost_application_count'] ?? null;
    $estimatedCost = $plan['estimated_cost'] ?? null;

    if (
        !is_array($applications) ||
        count($applications) !== count($allowedEvaluators) ||
        !is_int($paidCalls) ||
        $paidCalls < 0 ||
        $paidCalls > count($allowedEvaluators) ||
        !is_int($unknownCostCalls) ||
        $unknownCostCalls !== 0 ||
        !(is_int($estimatedCost) || is_float($estimatedCost)) ||
        !is_finite((float) $estimatedCost) ||
        $estimatedCost < 0 ||
        $estimatedCost > $maxEstimatedCost
    ) {
        return false;
    }

    $plannedEvaluators = [];
    $runCount = 0;

    foreach ($applications as $application) {
        if (!is_array($application)) {
            return false;
        }

        $evaluator = $application['evaluator'] ?? null;
        $action = $application['action'] ?? null;

        if (!is_string($evaluator) ||
            !in_array($action, ['run', 'reuse', 'skip'], true)
        ) {
            return false;
        }

        $plannedEvaluators[] = $evaluator;

        if ($action === 'run') {
            $runCount++;
        }
    }

    $expectedEvaluators = $allowedEvaluators;

    sort($plannedEvaluators);
    sort($expectedEvaluators);

    return $plannedEvaluators === $expectedEvaluators
        && $runCount === $paidCalls;
}
