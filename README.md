# Real-time Trending Keywords Detection.

### Architecture
- A crawler system. Crawl articles from various sources and transfer data to RabbitMQ.
- A processing system received data from RabbitMQ and extract keywords & trending keywords.
- A visualization system including Kibana.

### Run
```
docker-compose up
```
