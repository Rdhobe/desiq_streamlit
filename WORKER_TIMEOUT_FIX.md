# Worker Timeout Fix Documentation

## Issue Analysis

The application was experiencing worker timeouts during OpenAI API calls, particularly when generating scenarios, questions, and reports. The logs showed:

```
[2025-05-12 16:08:50 +0000] [65] [CRITICAL] WORKER TIMEOUT (pid:66)
[2025-05-12 16:08:50 +0000] [66] [INFO] Worker exiting (pid: 66)
[2025-05-12 16:08:51 +0000] [65] [ERROR] Worker (pid:66) was sent SIGKILL! Perhaps out of memory?
```

These errors occurred during scenario generation with OpenAI for the `finance`, `ethics`, and `relationships` categories.

## Root Causes

1. **Long-running API calls**: OpenAI API calls were taking too long to complete, exceeding the Gunicorn worker timeout of 60 seconds.
2. **Memory issues**: The worker process was likely using too much memory, causing the system to kill it.
3. **No timeout handling**: No mechanism was in place to gracefully handle API timeouts or prevent worker timeouts.
4. **No resource monitoring**: The application wasn't monitoring resource usage to prevent timeouts.

## Implemented Solutions

### 1. Refactored OpenAI Integration (`core/utils.py`)

- Created a centralized `safe_openai_call()` function with:
  - Proper error handling for API timeouts, rate limits, and connection errors
  - ThreadPoolExecutor with timeout control to prevent blocking
  - Improved caching for similar requests
  - Reduced token limits to decrease processing time

- Updated all OpenAI functions:
  - `generate_scenario_with_openai`
  - `generate_next_question`
  - `generate_final_report`

- Reduced complexity:
  - Shortened prompts
  - Decreased max tokens for responses
  - Improved fallback mechanisms
  - Enhanced caching strategies

### 2. Added Worker Timeout Middleware

Created a new `WorkerTimeoutMiddleware` in `core/middleware.py` that:

- Monitors resource usage (time and memory) during request processing
- Uses signal handlers to enforce time limits
- Implements concurrent request limiting for resource-intensive operations
- Provides graceful error responses when resources are constrained
- Returns helpful error pages explaining the situation to users

### 3. Added Error Template

Created a new `503.html` template for service unavailable responses that:

- Informs users about the temporary unavailability
- Suggests alternative approaches
- Provides clear next steps

### 4. Updated Gunicorn Configuration

Enhanced `gunicorn_config.py` with:

- Memory usage monitoring for workers
- Better worker lifecycle management
- Health check endpoint
- Enhanced logging for worker incidents
- Adjusted max requests to prevent memory leaks

### 5. Updated Settings

Added new configuration options in `settings.py`:

- Worker timeout settings
- Memory limits
- AI request concurrent limits
- Model configuration settings

### 6. Added Dependencies

Added `psutil` to `requirements.txt` for memory monitoring.

## How This Prevents Future Timeouts

1. **Proactive Monitoring**: The application now monitors time and memory usage, terminating requests before they trigger worker timeouts.

2. **Graceful Error Handling**: Instead of worker crashes, users receive informative error messages.

3. **Resource Management**: Limits on concurrent resource-intensive operations prevent system overload.

4. **Improved Caching**: Enhanced caching reduces repeated API calls and processing.

5. **Optimized API Usage**: Shorter prompts and smaller token limits reduce processing time.

6. **Worker Health Checks**: Gunicorn now monitors worker health and memory usage.

## Usage in Production

The system should now handle high-load situations much better by:

1. Limiting concurrent AI-intensive operations
2. Providing meaningful feedback to users during capacity issues
3. Auto-recovering from potential timeout situations
4. Ensuring consistent service availability

## Monitoring Recommendations

1. Monitor the following logs for signs of resource constraints:
   - `High-risk request completed` messages
   - `Resource-intensive request` warnings
   - `Request terminated to prevent worker timeout` errors

2. Adjust the following settings based on observed performance:
   - `WORKER_TIME_LIMIT`
   - `WORKER_MEMORY_LIMIT_MB`
   - `MAX_CONCURRENT_AI_REQUESTS`
   - Token limits in `AI_MODEL_MAX_TOKENS` 