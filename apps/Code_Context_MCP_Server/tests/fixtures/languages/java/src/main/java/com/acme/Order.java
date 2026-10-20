package com.acme;

import com.acme.util.Money;
import com.acme.util.*;
import java.util.List;

/**
 * An order of items.
 * @author someone
 */
public class Order {
    private final List<String> items;

    public Order(List<String> items) {
        this.items = items;
    }

    @Override
    public int total() {
        Money m = new Money(1);
        return m.add(sum()) + Math.max(1, 2);
    }

    int sum() {
        return this.items.size();
    }

    interface Line {
        int qty();
    }

    record Item(String id) {}

    enum State {
        OPEN,
        CLOSED
    }
}
