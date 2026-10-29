<?php
declare(strict_types=1);

require_once dirname(__DIR__) . '/includes/standalone_preflight_validation.php';

$allowedEvaluators = [
    'citation_support',
    'citation_coverage',
];

$validPlan = [
    'applications' => [
        ['evaluator' => 'citation_support', 'action' => 'run'],
        ['evaluator' => 'citation_coverage', 'action' => 'run'],
    ],
    'paid_application_count' => 2,
    'unknown_cost_application_count' => 0,
    'estimated_cost' => 0.015,
];

$testCases = [
    'Valid citation scoring plan' => [
        'plan' => $validPlan,
        'expected' => true,
    ],
    'Cost exceeds limit' => [
        'plan' => array_replace(
            $validPlan,
            ['estimated_cost' => 0.30]
        ),
        'expected' => false,
    ],
    'Unknown cost' => [
        'plan' => array_replace(
            $validPlan,
            ['unknown_cost_application_count' => 1]
        ),
        'expected' => false,
    ],
    'Unexpected evaluator' => [
        'plan' => array_replace(
            $validPlan,
            [
                'applications' => [
                    ['evaluator' => 'citation_support', 'action' => 'run'],
                    ['evaluator' => 'unexpected_evaluator', 'action' => 'run'],
                ],
            ]
        ),
        'expected' => false,
    ],
    'Mismatched paid-call count' => [
        'plan' => array_replace(
            $validPlan,
            ['paid_application_count' => 1]
        ),
        'expected' => false,
    ],
    'Skipped evaluator with mismatched paid-call count' => [
        'plan' => array_replace(
            $validPlan,
            [
                'applications' => [
                    ['evaluator' => 'citation_support', 'action' => 'run'],
                    ['evaluator' => 'citation_coverage', 'action' => 'skip'],
                ],
            ]
        ),
        'expected' => false,
    ],
    'Valid skipped citation support with coverage run' => [
        'plan' => array_replace(
            $validPlan,
            [
                'applications' => [
                    ['evaluator' => 'citation_support', 'action' => 'skip'],
                    ['evaluator' => 'citation_coverage', 'action' => 'run'],
                ],
                'paid_application_count' => 1,
                'estimated_cost' => 0.0075,
            ]
        ),
        'expected' => true,
    ],
    'Missing cost estimate' => [
        'plan' => array_replace(
            $validPlan,
            ['estimated_cost' => null]
        ),
        'expected' => false,
    ],
    'Reusable evaluator result' => [
        'plan' => array_replace(
            $validPlan,
            [
                'applications' => [
                    ['evaluator' => 'citation_support', 'action' => 'reuse'],
                    ['evaluator' => 'citation_coverage', 'action' => 'run'],
                ],
                'paid_application_count' => 1,
            ]
        ),
        'expected' => true,
    ],
];

$failures = 0;

foreach ($testCases as $name => $testCase) {
    $actual = validateStandalonePreflight(
        $testCase['plan'],
        $allowedEvaluators,
        0.25
    );

    $passed = $actual === $testCase['expected'];

    echo ($passed ? 'PASS' : 'FAIL') . ': ' . $name . PHP_EOL;

    if (!$passed) {
        $failures++;
    }
}

echo PHP_EOL;
echo count($testCases) - $failures
    . '/' . count($testCases)
    . ' tests passed.' . PHP_EOL;

exit($failures === 0 ? 0 : 1);
