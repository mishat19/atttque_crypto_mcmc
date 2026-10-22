import matplotlib.pyplot as plt
# Partie 1
x=[]
y=[]
for i in range(1,100,2):
    x.append(i)
    y.append(i*i)
    print(x)
    print(y)

# Partie 2
plt.plot(x, y, marker='.', linestyle='-', color='b', label='square')
plt.xlabel('Abscisses')
plt.ylabel('Ordonnés')
plt.show()