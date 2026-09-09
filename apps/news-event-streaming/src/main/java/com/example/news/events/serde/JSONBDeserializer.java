package com.example.news.events.serde;

import java.nio.ByteBuffer;

import com.oracle.spring.json.jsonb.JSONB;
import org.apache.kafka.common.serialization.Deserializer;


/**
 * The JSONBDeserializer converts Oracle JSONB byte arrays to Java objects.
 * @param <T> deserialization type
 */
public class JSONBDeserializer<T> implements Deserializer<T> {
    private final JSONB jsonb;
    private final Class<T> clazz;

    public JSONBDeserializer(JSONB jsonb, Class<T> clazz) {
        this.jsonb = jsonb;
        this.clazz = clazz;
    }

    @Override
    public T deserialize(String s, byte[] bytes) {
        return jsonb.fromOSON(ByteBuffer.wrap(bytes), clazz);
    }
}
