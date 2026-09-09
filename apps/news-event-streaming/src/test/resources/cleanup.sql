
-- Clean up TxEventQ
begin
    dbms_aqadm.stop_queue(
            queue_name => 'news_raw'
    );
    dbms_aqadm.drop_transactional_event_queue(
            queue_name => 'news_raw'
    );

    dbms_aqadm.stop_queue(
            queue_name => 'news_parsed'
    );
    dbms_aqadm.drop_transactional_event_queue(
            queue_name => 'news_parsed'
    );
end;
/

-- Clean up database tables
drop view news_dv;
drop index news_vector_ivf_idx;
drop table news_vector cascade constraints ;
drop table news;
