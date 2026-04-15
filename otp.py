import random
def genotp():
    u_l=[chr(i) for i in range(ord("A"),ord("Z")+1)]
    s_l=[chr(i) for i in range(ord("a"),ord("z")+1)]
    otp=""
    for i in range(2):
        otp+=random.choice(u_l)+str(random.randint(1,10))+random.choice(s_l)    
    return otp


# def genotp():
#     otp=""
#     for i in range(0,6):
#         otp+=str(random.randint(1,9))
#     return otp
# password=genotp()
# print(password)


 

