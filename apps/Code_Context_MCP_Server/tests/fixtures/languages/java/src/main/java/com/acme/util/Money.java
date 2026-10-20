package com.acme.util;

public class Money {
    private final int cents;

    public Money(int cents) {
        this.cents = cents;
    }

    public int add(int other) {
        return cents + other;
    }
}
