import js from "@eslint/js";

export default [
  js.configs.recommended,
  {
    files: ["src/imagegen/frontend/**/*.js", "tests/js/**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        AbortController: "readonly",
        Blob: "readonly",
        DataTransfer: "readonly",
        Event: "readonly",
        File: "readonly",
        FileReader: "readonly",
        FormData: "readonly",
        HTMLCanvasElement: "readonly",
        Image: "readonly",
        KeyboardEvent: "readonly",
        MouseEvent: "readonly",
        Response: "readonly",
        URL: "readonly",
        clearTimeout: "readonly",
        console: "readonly",
        document: "readonly",
        fetch: "readonly",
        globalThis: "readonly",
        queueMicrotask: "readonly",
        setTimeout: "readonly",
        window: "readonly",
      },
    },
  },
];
