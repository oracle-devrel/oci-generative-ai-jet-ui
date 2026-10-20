package com.acme

import com.acme.Money

/** A slug of the text. */
fun String.slug(): String {
    return lowercase().replace(" ", "-")
}

fun top(): Int {
    return 1
}

class Order(val id: String) {
    fun total(): Int {
        return sum() + Money(1).value
    }

    private fun sum(): Int {
        return id.length
    }

    companion object {
        fun create(): Order {
            return Order("x")
        }
    }
}

object Registry {
    fun all(): List<Order> {
        return listOf(Order.create())
    }
}

interface Shape {
    fun area(): Double
}

data class Point(val x: Int)

enum class Color {
    RED,
    GREEN,
}
