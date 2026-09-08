package com.example.hybrid;

import org.junit.jupiter.api.Test;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.oracle.OracleContainer;

import java.time.Duration;

@Testcontainers
class HybridSearchSampleTest {

    @Container
    static final OracleContainer oracle = new OracleContainer("gvenzl/oracle-free:23.26.3-full-faststart")
            .withStartupTimeout(Duration.ofMinutes(5))
            .withUsername("testuser")
            .withPassword("testpwd");

    @Test
    void runsMainAgainstOracleFree() throws Exception {
        HybridSearchSample.main(new String[]{
                oracle.getJdbcUrl(),
                oracle.getUsername(),
                oracle.getPassword()
        });
    }
}
