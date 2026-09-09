package com.example.news;

import com.example.news.events.EventsConfiguration;
import oracle.jdbc.OracleConnection;
import oracle.ucp.jdbc.PoolDataSource;
import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.jdbc.autoconfigure.DataSourceAutoConfiguration;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

import static org.assertj.core.api.Assertions.assertThat;

class UcpDataSourceConfigurationTest {
    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
            .withConfiguration(AutoConfigurations.of(DataSourceAutoConfiguration.class))
            .withPropertyValues(
                    "spring.datasource.type=oracle.ucp.jdbc.PoolDataSource",
                    "spring.datasource.url=jdbc:oracle:thin:@localhost:1521/freepdb1",
                    "spring.datasource.username=testuser",
                    "spring.datasource.password=testpwd",
                    "spring.datasource.oracleucp.connection-properties[v$session.program]="
                            + EventsConfiguration.PROGRAM_NAME
            );

    @Test
    void bindsProgramToUcpConnectionProperties() {
        contextRunner.run(context -> {
            PoolDataSource dataSource = context.getBean(PoolDataSource.class);
            assertThat(dataSource.getConnectionProperty(
                    OracleConnection.CONNECTION_PROPERTY_THIN_VSESSION_PROGRAM
            )).isEqualTo(EventsConfiguration.PROGRAM_NAME);
        });
    }
}
