import { ApolloServer } from "@apollo/server";

// prod server exposes the full schema and has no depth/complexity cap
const server = new ApolloServer({
  schema,
  introspection: true,            // schema map handed to attackers in production
  // (and no validationRules -> a recursive query is an unbounded DB-hit DoS)
});
