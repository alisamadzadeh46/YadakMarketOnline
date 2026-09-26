// ESLint flat config: Next.js core web vitals + TypeScript rules.
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const config = [
  ...nextVitals,
  ...nextTypescript,
  {
    rules: {
      // Product and blog images are served by Django/nginx at their final
      // size; the Next.js image optimizer is not deployed.
      "@next/next/no-img-element": "off",
      // API payloads are not typed end to end yet; new code should prefer
      // explicit types, so this stays visible as a warning.
      "@typescript-eslint/no-explicit-any": "warn",
      // Several pages reset local UI state when the route parameter changes;
      // the pattern is intentional and covered by the React docs' caveats.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts"],
  },
];

export default config;
