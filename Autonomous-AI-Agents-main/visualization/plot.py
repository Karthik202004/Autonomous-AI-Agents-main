import pandas as pd
from company_template import apply_company_template
import seaborn as sns
apply_company_template()

data = {
    'country': ['United States', 'China', 'Japan', 'Germany', 'France',
                'United Kingdom', 'India', 'Australia', 'South Korea', 'Brazil'],
    'sales': [123456789, 234567890, 345678901, 456789012, 567890123,
              678901234, 789012345, 890123456, 901234567, 102345678]
}
df = pd.DataFrame(data)

# Infer x-axis and y-axis
x_axis = df['country']
y_axis = df['sales']

import matplotlib.pyplot as plt

plt.figure(figsize=(10,6))
sns.barplot(x=x_axis, y=y_axis)
plt.title('Total Sales of Each Country')
plt.xlabel('Country')
plt.ylabel('Sales')

# Save the figure using plt.savefig()
plt.savefig("visualization/country_sales.png")
