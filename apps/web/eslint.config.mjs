import nextCoreWebVitals from "eslint-config-next/core-web-vitals";

const config = [
  ...nextCoreWebVitals,
  { ignores: [".next/**", "node_modules/**", "out/**"] },
  /** Product client surface: data-fetch-on-mount patterns trip strict react-hooks rules without a net UX win here. */
  {
    files: ["app/app/page.tsx"],
    rules: { "react-hooks/set-state-in-effect": "off" },
  },
];

export default config;
