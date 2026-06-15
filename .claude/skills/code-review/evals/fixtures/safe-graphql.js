import { ApolloServer } from "@apollo/server";
import depthLimit from "graphql-depth-limit";
import { createComplexityLimitRule } from "graphql-validation-complexity";

const server = new ApolloServer({
  schema,
  introspection: process.env.NODE_ENV !== "production",
  validationRules: [depthLimit(8), createComplexityLimitRule(1000)],
});
