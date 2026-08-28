import path from "node:path";

const candidate = process.env.CANDIDATE_FRONTEND;
if (!candidate) throw new Error("CANDIDATE_FRONTEND is required");

export default {
  resolve: {
    alias: {
      "@candidate": path.resolve(candidate),
    },
  },
  test: {
    environment: "happy-dom",
    include: [path.resolve(import.meta.dirname, "*.spec.ts")],
  },
};

