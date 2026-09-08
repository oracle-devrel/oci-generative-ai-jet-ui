package com.example.news.model;

import java.util.List;
import java.util.Objects;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class News {
    private String _id = UUID.randomUUID().toString();
    private String article;

    private List<NewsVector> news_vector;

    public String get_id() {
        return _id;
    }

    public void set_id(String _id) {
        this._id = _id;
    }

    public String getArticle() {
        return article;
    }

    public void setArticle(String article) {
        this.article = article;
    }

    public List<NewsVector> getNews_vector() {
        return news_vector;
    }

    public void setNews_vector(List<NewsVector> news_vector) {
        this.news_vector = news_vector;
    }

    @Override
    public boolean equals(Object o) {
        if (o == null || getClass() != o.getClass()) return false;
        News news = (News) o;
        return Objects.equals(_id, news._id) && Objects.equals(article, news.article);
    }

    @Override
    public int hashCode() {
        return Objects.hash(_id, article);
    }
}
