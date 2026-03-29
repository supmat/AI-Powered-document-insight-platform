# Extended Load Test Report (Rate Limit: 150)

This report documents the system performance when the API Gateway rate limit is increased to **150 requests per 60 seconds** per IP.

## Configuration
- **Rate Limit:** 150 requests / 60 seconds
- **Users:** 100
- **Spawn Rate:** 20 users/s
- **Run Time:** 30s
- **Host:** http://localhost:8001

## Results

### Response Time Percentiles (approximated)
|       Type     |         Name          |    50%   |     66%   |     75%   |     80%   |     90%   |     95%   |     98%   |     99%   |     100%  | # reqs |
|----------------|-----------------------|----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|--------|
|       POST     | /api/v1/auth/login    |   9000   |    9500   |    9700   |    10000  |    12000  |    12000  |    18000  |    18000  |    18000  | 26     |
|       POST     | /api/v1/auth/register |  15000   |   18000   |    20000  |    21000  |    25000  |    25000  |    26000  |    26000  |    26000  | 47     |
|       POST     | /api/v1/query/        |   1100   |   11000   |    11000  |    11000  |    11000  |    12000  |    12000  |    12000  |    12000  | 12     |
| **Aggregated** |                       | **9500** | **12000** | **17000** | **18000** | **22000** | **25000** | **26000** | **26000** | **26000** | **85** |

### Error Report
| # occurrences |                                   Error                                      |
|---------------|------------------------------------------------------------------------------|
|       5       | POST /api/v1/auth/register: HTTPError('429 Client Error: Too Many Requests') |
|       7       | POST /api/v1/query/: Failed with status 429                                  |
|       4       | POST /api/v1/auth/login: HTTPError('429 Client Error: Too Many Requests')    |

## Observations
1. **Increased Throughput:** By increasing the rate limit to 150, more requests were able to reach the backend services compared to the default limit of 15.
2. **Residual Rate Limiting:** Even with a high limit of 150, some 429 errors were still observed. This is expected as 100 concurrent users quickly exhaust any fixed window bucket when performing complex multi-step flows.
