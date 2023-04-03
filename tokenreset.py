from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
def token(rollno,seconds):
    s=Serializer('*345678xfgh*',seconds)
    return s.dumps({'user':rollno}).decode('utf-8')
