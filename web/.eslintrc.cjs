module.exports = {
  root: true,
  env: {
    es2023: true,
    node: true,
    browser: false,
  },
  extends: [
    'eslint:recommended',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  rules: {},
};

