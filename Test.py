conns = []
while True:
    conn, add = s.accept()
    if len(conns) < MAX_PLAYER:
        conns.append(conn)
        if len(conns) == MAX_PLAYER:
            # Tạo 1 thread mới truyền cái conns vào để bắt đầu game
            # Hết game thì set lại cái conns = []
    else:
        refuse()


