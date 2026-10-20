// ESLint configuration (flat config format, ESLint >= 9)
// Usage: make lint_js
import js from '@eslint/js';
import globals from 'globals';

export default [
    {
        ignores: ['**/vendor*', '**/*.min.js', 'submodules/**', '**/odm/**', 'htmlcov/**'],
    },
    js.configs.recommended,
    {
        files: ['**/*.js'],
        languageOptions: {
            ecmaVersion: 2017,
            sourceType: 'script',
            globals: {
                ...globals.browser,
                ...globals.jquery,
            },
        },
        linterOptions: {
            reportUnusedDisableDirectives: 'error',
        },
        rules: {
            'indent': ['error', 4, {'SwitchCase': 1, 'ArrayExpression': 'first', 'ObjectExpression': 'first'}],
            'no-trailing-spaces': 'error',
            'no-unneeded-ternary': 'error',
            'no-whitespace-before-property': 'error',
            'no-multi-spaces': 'error',
            'curly': 'error',
            'brace-style': 'error',
            'semi-spacing': 'error',
            'space-before-blocks': 'error',
            'switch-colon-spacing': 'error',
            'no-var': 'warn',
            'prefer-const': 'warn',
            'key-spacing': 'error',
            'func-call-spacing': 'error',
            'keyword-spacing': 'error',
            'space-infix-ops': 'error',
            'no-use-before-define': 'error',
            'space-unary-ops': ['error', {'words': true, 'nonwords': false}],
            'space-in-parens': ['error', 'never'],
            'quotes': ['error', 'single'],
            'space-before-function-paren': ['error', {'anonymous': 'always'}],
            'camelcase': ['error', {'properties': 'always', 'ignoreImports': true, 'ignoreGlobals': true, 'ignoreDestructuring': true}],
            'semi': ['error', 'always'],
        },
    },
];
