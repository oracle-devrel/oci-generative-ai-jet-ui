begin
    execute immediate 'drop table hybrid_documents purge';
exception
    when others then
        if sqlcode != -942 then
            raise;
        end if;
end;
/

create table hybrid_documents (
    id number generated always as identity primary key,
    title varchar2(200) not null unique,
    content clob not null,
    category varchar2(30) not null,
    price number(10,2) not null,
    metadata json not null,
    embedding vector(384, FLOAT32) annotations(Distance 'COSINE', IndexType 'IVF')
)
/

create vector index hybrid_documents_vector_idx
on hybrid_documents (embedding)
organization neighbor partitions
distance COSINE
with target accuracy 95
parameters (type IVF, neighbor partitions 4)
/

create index hybrid_documents_category_price_idx
on hybrid_documents (category, price)
/
