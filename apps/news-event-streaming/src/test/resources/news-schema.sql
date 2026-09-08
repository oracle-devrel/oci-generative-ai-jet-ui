-- News articles
create table if not exists news (
    news_id    varchar2(36) default sys_guid() primary key,
    article    clob
);

-- News Vectors, many-to-one with news
create table if not exists news_vector (
    id        varchar2(36) default sys_guid() primary key,
    news_id   varchar2(36) ,
    chunk     varchar2(2500),
    -- you may need to change the dimensions used depending on your embedding model
    embedding vector(384, FLOAT64) annotations(Distance 'COSINE', IndexType 'IVF'),
    constraint fk_news_vector foreign key (news_id)
    references news(news_id) on delete cascade
);

-- Vector index for News Vectors
create vector index if not exists news_vector_ivf_idx on news_vector (embedding) organization neighbor partitions
distance COSINE
with target accuracy 90
parameters (type IVF, neighbor partitions 10);

-- JSON Relational Duality View for the News Schema
create or replace force editionable json relational duality view news_dv
 as
news @insert @update @delete {
    _id : news_id
    article
    news_vector @insert @update @delete
             @link (to : [NEWS_ID]) {
        id
        chunk
        embedding
    }
}
/