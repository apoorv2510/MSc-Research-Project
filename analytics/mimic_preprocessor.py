import pandas as pd
from sklearn.preprocessing import LabelEncoder

def load_and_prepare_mimic(path="D:\\Research\\mimic-iii-clinical-database-demo-1.4\\mimic-iii-clinical-database-demo-1.4\\DRGCODES.csv"):
    df = pd.read_csv(path)
    
    # Drop NA drg_type
    df = df.dropna(subset=["drg_type"])
    
    # Encode 'drg_type'
    encoder = LabelEncoder()
    df["drg_type_encoded"] = encoder.fit_transform(df["drg_type"])
    
    print("Encoding Map:", dict(zip(encoder.classes_, encoder.transform(encoder.classes_))))
    
    return df["drg_type_encoded"].tolist()

