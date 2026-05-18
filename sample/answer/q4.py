def circle():
    result = 3.14 * r ** 2    #r은      전역 변수
    return result             #result는 지역 변수

r = float(input())
area = circle()
print(area)
