#함수 안에서 전역변수의 값을 변경하고 싶은 경우
#result = 0                 # 전역변수
def circle():
    global result            # 전역변수 result를 사용하겠다!
    result = 3.14 * r ** 2

result = 0
r = float(input())
circle()
print(result)
