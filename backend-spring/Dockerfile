# ============================================================
# Adelie Investment - Spring Boot Backend
# ============================================================
FROM eclipse-temurin:17-jdk AS builder
WORKDIR /app

# Gradle wrapper 복사 + 의존성 다운로드 (캐시 최적화)
COPY gradlew .
COPY gradle gradle
RUN chmod +x gradlew

COPY build.gradle settings.gradle ./
RUN ./gradlew dependencies --no-daemon 2>/dev/null || true

# 소스 복사 + 빌드
COPY src src
RUN ./gradlew bootJar --no-daemon -x test

# ============================================================
# Runtime: JRE only
# ============================================================
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=builder /app/build/libs/*.jar app.jar

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8083/api/health || exit 1

EXPOSE 8083
ENTRYPOINT ["java", "-Xmx512m", "-jar", "app.jar"]
