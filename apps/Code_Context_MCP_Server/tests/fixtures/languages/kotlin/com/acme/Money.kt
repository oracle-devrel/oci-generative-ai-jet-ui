package com.acme

class Money(val value: Int) {
    fun plus(other: Money): Money {
        return Money(value + other.value)
    }
}
