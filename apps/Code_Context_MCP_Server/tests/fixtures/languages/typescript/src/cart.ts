import { get } from "./api/client";
import * as api from "./api";
import type { Id } from "./types";

/**
 * Adds two numbers.
 * @param a the first
 */
export function add(a: number, b: number): number {
  return helper(a) + b;
}

function helper(x: number): number {
  return x;
}

export const twice = (x: number) => add(x, x);

export interface Shape {
  area(): number;
}

export type Pair = [number, number];

export enum Color {
  Red,
  Green,
}

export class Cart implements Shape {
  constructor(private items: number[]) {}

  area(): number {
    return this.total() + api.count();
  }

  private total(): number {
    return get("/total") + Math.max(1, 2);
  }

  #secret(): number {
    return new Cart([]).area();
  }
}
