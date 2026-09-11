package com.example.hybrid;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;
import java.io.IOException;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.oracle.OracleContainer;
import org.testcontainers.utility.MountableFile;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Duration;

@Testcontainers
class HybridSearchSampleTest {

    @Container
    static final OracleContainer oracle = new OracleContainer("gvenzl/oracle-free:23.26.3-full-faststart")
            .withStartupTimeout(Duration.ofMinutes(5))
            .withUsername("testuser")
            .withPassword("testpwd");

    @BeforeAll
    static void grantSessionViewAccess() throws IOException, InterruptedException {
        oracle.copyFileToContainer(MountableFile.forClasspathResource("grant-session-view.sql"), "/tmp/grant-session-view.sql");
        OracleContainer.ExecResult result = oracle.execInContainer("sqlplus", "sys / as sysdba", "@/tmp/grant-session-view.sql");
        assertThat(result.getExitCode()).isZero();
    }

    @Test
    void runsMainAgainstOracleFree() throws Exception {
        try (Connection connection = HybridSearchSample.createDataSource(
                oracle.getJdbcUrl(),
                oracle.getUsername(),
                oracle.getPassword()
        ).getConnection();
             Statement statement = connection.createStatement();
             ResultSet resultSet = statement.executeQuery("""
                     select program
                     from v$session
                     where audsid = sys_context('USERENV', 'SESSIONID')
                     """)) {
            assertThat(resultSet.next()).isTrue();
            assertThat(resultSet.getString(1)).isEqualTo(HybridSearchSample.PROGRAM_NAME);
        }

        HybridSearchSample.main(new String[]{
                oracle.getJdbcUrl(),
                oracle.getUsername(),
                oracle.getPassword()
        });
    }
}
