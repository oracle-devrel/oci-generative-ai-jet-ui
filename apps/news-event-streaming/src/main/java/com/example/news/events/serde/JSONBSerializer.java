package com.example.news.events.serde;

import com.oracle.spring.json.jsonb.JSONB;
import org.apache.kafka.common.serialization.Serializer;

/**
 * The JSONBSerializer converts Java objects to an Oracle JSONB byte array.
 * @param <T> serialization type.
 */
public class JSONBSerializer<T> implements Serializer<T> {
    private final JSONB jsonb;

    public JSONBSerializer(JSONB jsonb) {
        this.jsonb = jsonb;
    }

    @Override
    public byte[] serialize(String s, T obj) {
        return jsonb.toOSON(obj);
    }
}
