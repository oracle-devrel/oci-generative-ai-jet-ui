import { handle } from "hono/aws-lambda";
import { createApp } from "./app.js";

export const handler = handle(createApp());
