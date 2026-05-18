def fact(k):
	if k<=1:
		return 1
	return fact(k-1) * k

a =  int(input())
result = fact(a)
print(result)