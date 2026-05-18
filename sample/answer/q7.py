def fibo(n):
    # 1. 탈출 조건: 1번째와 2번째 값은 항상 1
    if n <= 2:
        return 1

    # 2. 재귀 케이스: 앞의 두 수를 더함
    return fibo(n - 1) + fibo(n - 2)

# 메인 실행부: 10번째 값을 구함
result = fibo(10)
print(result)