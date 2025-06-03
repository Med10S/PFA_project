"""
Re-entraînement du modèle MLP avec la méthode exacte du notebook pasteCode.ipynb
Utilise l'entraînement progressif préféré par l'utilisateur
Produit un modèle compatible avec le système (42 features, nom correct)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os
import logging
import warnings
import time
import winsound
from tqdm import tqdm

from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split, learning_curve, RandomizedSearchCV
from sklearn.metrics import accuracy_score, log_loss, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.neural_network import MLPClassifier
from sklearn.exceptions import ConvergenceWarning

# Supprimer les avertissements non nécessaires
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=ConvergenceWarning)

# Création des dossiers pour les résultats
os.makedirs('figures/mlp', exist_ok=True)
os.makedirs('models', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_and_preprocess_data(filepath, test_size=0.2, val_size=0.15, random_state=42):
    """
    Charge et prétraite les données pour l'entraînement MLP
    EXACTEMENT comme dans pasteCode.ipynb
    Assure la compatibilité avec 42 features (sans colonne 'id')
    """
    print(f"Chargement et prétraitement des données depuis {filepath}...")
    
    # Vérifier l'existence du fichier
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Le fichier {filepath} n'existe pas.")
    
    # Charger les données avec gestion d'erreurs
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise Exception(f"Erreur lors du chargement du fichier CSV: {str(e)}")
    
    print(f"Données chargées: {df.shape[0]} lignes et {df.shape[1]} colonnes")
    
    # Vérifier que les colonnes obligatoires sont présentes
    required_cols = ['label']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Colonnes requises manquantes. Assurez-vous que {required_cols} sont présentes.")
    
    # **CRITIQUE**: Supprimer les colonnes non nécessaires (EXACTEMENT comme dans le notebook)
    # Cela garantit 42 features au lieu de 43 (compatible avec le système)
    df_processed = df.drop(columns=['id', 'attack_cat'], errors='ignore')
    
    print(f"Colonnes après suppression de 'id' et 'attack_cat': {df_processed.shape[1]} colonnes")
    
    # Afficher les informations sur les valeurs manquantes
    missing_values = df_processed.isnull().sum()
    missing_cols = missing_values[missing_values > 0]
    if not missing_cols.empty:
        print(f"Valeurs manquantes détectées dans les colonnes suivantes:")
        for col, count in missing_cols.items():
            print(f"  - {col}: {count} valeurs manquantes ({(count/len(df_processed))*100:.2f}%)")
    
    # Gérer les valeurs manquantes - considérer l'imputation plutôt que la suppression
    rows_before = df_processed.shape[0]
    df_processed = df_processed.dropna()
    rows_after = df_processed.shape[0]
    if rows_before > rows_after:
        print(f"Suppression de {rows_before - rows_after} lignes avec des valeurs manquantes ({(rows_before - rows_after) / rows_before * 100:.2f}%)")
    
    # Séparer les caractéristiques et les étiquettes
    X = df_processed.drop(columns=['label'], errors='ignore')
    y = df_processed['label']  # 0 pour normal, 1 pour attaque
    
    print(f"Features finales: {X.shape[1]} colonnes (compatible avec le système)")
    
    # Vérifier la distribution des classes
    class_counts = y.value_counts()
    print(f"Distribution des classes:")
    for cls, count in class_counts.items():
        print(f"  - Classe {cls}: {count} échantillons ({count/len(y)*100:.2f}%)")
    
    # Encoder les caractéristiques catégorielles
    label_encoders = {}
    categorical_cols = X.select_dtypes(include=['object', 'category']).columns
    if len(categorical_cols) > 0:
        print(f"Encodage des {len(categorical_cols)} colonnes catégorielles:")
        for col in categorical_cols:
            unique_values = X[col].nunique()
            print(f"  - {col}: {unique_values} valeurs uniques")
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))  # Convertir en string pour éviter les erreurs
            label_encoders[col] = le
    
    # Mise à l'échelle des caractéristiques numériques
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print(f"Forme finale des données après preprocessing: {X_scaled.shape}")
    
    # Division en ensembles d'entraînement, validation et test avec stratification
    try:
        # D'abord, séparer les données de test
        X_temp, X_test, y_temp, y_test = train_test_split(
            X_scaled, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # Ensuite, diviser les données restantes en ensembles d'entraînement et de validation
        val_ratio = val_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=val_ratio, random_state=random_state, stratify=y_temp
        )
    except ValueError as e:
        # Si la stratification échoue (par exemple, trop peu d'échantillons dans une classe)
        print(f"Avertissement lors de la stratification: {str(e)}")
        print("Tentative de division sans stratification...")
        X_temp, X_test, y_temp, y_test = train_test_split(
            X_scaled, y, test_size=test_size, random_state=random_state
        )
        val_ratio = val_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=val_ratio, random_state=random_state
        )
    
    print(f"Dimensions des ensembles de données:")
    print(f"  Train: X={X_train.shape}, y={y_train.shape}")
    print(f"  Validation: X={X_val.shape}, y={y_val.shape}")
    print(f"  Test: X={X_test.shape}, y={y_test.shape}")
    
    # Vérifier les distributions des classes dans chaque ensemble
    print(f"Distribution des classes dans les ensembles:")
    print(f"  Train: {np.bincount(y_train.astype(int))}")
    print(f"  Validation: {np.bincount(y_val.astype(int))}")
    print(f"  Test: {np.bincount(y_test.astype(int))}")
    
    return X_train, X_val, X_test, y_train, y_val, y_test, scaler, label_encoders


def optimize_mlp_hyperparameters(X_train, y_train, X_val, y_val, cv=3):
    """
    Optimise les hyperparamètres du modèle MLP
    EXACTEMENT comme dans pasteCode.ipynb
    """
    print(f"Optimisation des hyperparamètres MLP...")
    
    param_dist = {
        'hidden_layer_sizes': [(64,), (128,), (64, 32), (128, 64)],
        'activation': ['relu', 'tanh'],
        'solver': ['adam', 'sgd'],
        'alpha': [0.0001, 0.001],
        'learning_rate': ['constant', 'adaptive']
    }

    mlp = MLPClassifier(max_iter=200, early_stopping=True, random_state=42)
    grid_search = RandomizedSearchCV(
        mlp, param_distributions=param_dist, n_iter=15, cv=cv, scoring='accuracy', n_jobs=-1, verbose=1
    )

    start_time = time.time()
    grid_search.fit(X_train, y_train)
    search_time = time.time() - start_time
    print(f"Recherche par grille terminée en {search_time:.2f} secondes")

    val_score = accuracy_score(y_val, grid_search.predict(X_val))
    print(f"Meilleurs hyperparamètres: {grid_search.best_params_}")
    print(f"Score de validation croisée: {grid_search.best_score_:.4f}")
    print(f"Score sur l'ensemble de validation: {val_score:.4f}")

    return grid_search.best_params_, val_score


def plot_training_metrics(
     train_accuracies, val_accuracies, train_losses, val_losses,
     train_f1s, val_f1s, train_recalls, val_recalls, n_epochs,
     algorithm_name="MLP", output_dir="figures/mlp"):
     """
     Fonction dédiée pour tracer les métriques d'entraînement et enregistrer chaque graphe dans un fichier séparé.
     EXACTEMENT comme dans pasteCode.ipynb
     """
     # Style commun pour tous les graphiques
     metrics = {
          'Accuracy': (train_accuracies, val_accuracies),
          'Loss': (train_losses, val_losses),
          'F1 Score': (train_f1s, val_f1s),
          'Recall': (train_recalls, val_recalls)
     }

     for metric_name, (train_metric, val_metric) in metrics.items():
          fig, ax = plt.subplots(figsize=(10, 6))
          ax.grid(True, linestyle='--', alpha=0.7)
          ax.set_axisbelow(True)  # Placer la grille derrière les données

          # Graphique de la métrique
          ax.plot(range(1, n_epochs + 1), train_metric, '-o', label='Entraînement', color='#1f77b4',
                    linewidth=2, markersize=5, alpha=0.8)
          ax.plot(range(1, n_epochs + 1), val_metric, '-o', label='Validation', color='#ff7f0e',
                    linewidth=2, markersize=5, alpha=0.8)
          ax.set_title(f'{algorithm_name} - {metric_name}', fontsize=16, fontweight='bold')
          ax.set_xlabel('Époque', fontsize=14)
          ax.set_ylabel(metric_name, fontsize=14)
          ax.legend(fontsize=12)

          # Ajouter des annotations pour les valeurs maximales (validation)
          max_val_metric = max(val_metric)
          max_val_metric_idx = val_metric.index(max_val_metric)
          ax.annotate(f'Max: {max_val_metric:.4f}',
                         xy=(max_val_metric_idx + 1, max_val_metric),
                         xytext=(max_val_metric_idx + 1, max_val_metric - 0.05),
                         arrowprops=dict(facecolor='black', shrink=0.05),
                         fontsize=12, ha='center')

          plt.tight_layout()

          # Assurer que le répertoire de sortie existe
          os.makedirs(output_dir, exist_ok=True)
          output_path = os.path.join(output_dir, f'{algorithm_name.lower()}_{metric_name.lower().replace(" ", "_")}.png')
          plt.savefig(output_path, dpi=300, bbox_inches='tight')
          print(f"✅ Métriques d'entraînement enregistrées dans {output_path}")
          plt.close(fig)


def train_mlp_progressive(X_train, y_train, X_val, y_val, X_test, y_test, best_params, n_epochs=25):
    """
    Entraîne le modèle MLP de manière progressive en augmentant la taille de l'ensemble d'entraînement
    EXACTEMENT comme dans pasteCode.ipynb avec l'entraînement progressif préféré
    """
    print(f"Entraînement progressif du MLP sur {n_epochs} époques...")

    # Convertir en tableaux NumPy pour éviter les problèmes d'indexation
    if not isinstance(X_train, np.ndarray):
        X_train = np.array(X_train)
    if not isinstance(y_train, np.ndarray):
        y_train = np.array(y_train)
    if not isinstance(X_val, np.ndarray):
        X_val = np.array(X_val)
    if not isinstance(y_val, np.ndarray):
        y_val = np.array(y_val)
    if not isinstance(X_test, np.ndarray):
        X_test = np.array(X_test)
    if not isinstance(y_test, np.ndarray):
        y_test = np.array(y_test)

    # Vérifier si l'entraînement est possible
    if len(X_train) == 0 or len(y_train) == 0:
        raise ValueError("Ensembles d'entraînement vides")
    if len(np.unique(y_train)) < 2:
        raise ValueError("L'ensemble d'entraînement doit contenir au moins deux classes différentes")

    # Métriques (EXACTEMENT comme dans le notebook)
    train_accuracies = []
    val_accuracies = []
    train_precisions = []
    val_precisions = []
    train_recalls = []
    val_recalls = []
    train_f1s = []
    val_f1s = []
    train_losses = []
    val_losses = []
    epoch_train_sizes = []

    # Initialiser le modèle avec les meilleurs paramètres
    model = MLPClassifier(**best_params, random_state=42)

    # Meilleur modèle
    best_model = None
    best_val_acc = 0

    # Valeurs pour l'augmentation progressive de la taille de l'ensemble d'entraînement
    train_ratio_start = 0.2  # Commence avec 20% des données
    train_ratio_end = 1.0    # Termine avec 100% des données

    # Assurer une répartition équilibrée des classes lors de l'échantillonnage
    class_indices = {}
    unique_classes = np.unique(y_train)
    for cls in unique_classes:
        class_indices[cls] = np.where(y_train == cls)[0]

    with tqdm(total=n_epochs, desc="Entraînement MLP") as pbar:
        for epoch in range(n_epochs):
            try:
                # Augmentation progressive de la taille de l'entraînement
                train_ratio = train_ratio_start + (train_ratio_end - train_ratio_start) * (epoch / max(1, n_epochs-1))
                indices = []
                for cls in unique_classes:
                    n_samples = int(len(class_indices[cls]) * train_ratio)
                    if n_samples > 0:
                        cls_sample = np.random.choice(class_indices[cls], n_samples, replace=False)
                        indices.extend(cls_sample)
                np.random.shuffle(indices)
                train_size = len(indices)
                epoch_train_sizes.append(train_size)
                
                # Extraire les données d'entraînement pour cette époque
                X_epoch = X_train[indices]
                y_epoch = y_train[indices]

                # Créer et entraîner le modèle avec les meilleurs hyperparamètres
                model.fit(X_epoch, y_epoch)

                # Évaluations
                train_pred = model.predict(X_epoch)
                val_pred = model.predict(X_val)

                train_acc = accuracy_score(y_epoch, train_pred)
                val_acc = accuracy_score(y_val, val_pred)
                train_prec = precision_score(y_epoch, train_pred, zero_division=0)
                val_prec = precision_score(y_val, val_pred, zero_division=0)
                train_rec = recall_score(y_epoch, train_pred, zero_division=0)
                val_rec = recall_score(y_val, val_pred, zero_division=0)
                train_f1 = f1_score(y_epoch, train_pred, zero_division=0)
                val_f1 = f1_score(y_val, val_pred, zero_division=0)

                train_accuracies.append(train_acc)
                val_accuracies.append(val_acc)
                train_precisions.append(train_prec)
                val_precisions.append(val_prec)
                train_recalls.append(train_rec)
                val_recalls.append(val_rec)
                train_f1s.append(train_f1)
                val_f1s.append(val_f1)

                # Calcul des pertes (log loss) si predict_proba est disponible
                if hasattr(model, 'predict_proba'):
                    try:
                        train_probs = model.predict_proba(X_epoch)
                        val_probs = model.predict_proba(X_val)
                        # Vérifier la validité des probabilités
                        if not np.any(np.isnan(train_probs)) and not np.any(np.isnan(val_probs)):
                            train_loss = log_loss(y_epoch, train_probs)
                            val_loss = log_loss(y_val, val_probs)
                        else:
                            train_loss = -np.log(max(0.001, train_acc))
                            val_loss = -np.log(max(0.001, val_acc))
                    except Exception:
                        # En cas d'erreur, utiliser une approximation
                        train_loss = -np.log(max(0.001, train_acc))
                        val_loss = -np.log(max(0.001, val_acc))
                else:
                    # Si predict_proba n'est pas disponible, simuler une relation inverse avec l'accuracy
                    train_loss = -np.log(max(0.001, train_acc))
                    val_loss = -np.log(max(0.001, val_acc))

                train_losses.append(train_loss)
                val_losses.append(val_loss)

                pbar.update(1)
                pbar.set_postfix({
                    'Train Acc': f'{train_acc:.4f}',
                    'Val Acc': f'{val_acc:.4f}',
                    'Train Size': train_size
                })

                # Suivre le meilleur modèle
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    best_model = model

            except Exception as e:
                print(f"\nErreur à l'époque {epoch+1}: {str(e)}")
                continue

    # Si aucun modèle valide n'a été trouvé, utiliser un modèle par défaut
    if best_model is None:
        print("Aucun modèle valide trouvé pendant l'entraînement. Création d'un modèle par défaut.")
        best_model = MLPClassifier(**best_params, random_state=42)
        best_model.fit(X_train, y_train)
    
    # Tracer les métriques d'entraînement (EXACTEMENT comme dans le notebook)
    try:
        plot_training_metrics(train_accuracies, val_accuracies, train_losses, val_losses, 
                             train_f1s, val_f1s, train_recalls, val_recalls, n_epochs,
                             algorithm_name="MLP", output_dir="figures/mlp")
        
        # Graphique de la taille de l'ensemble d'entraînement
        plt.figure(figsize=(10, 5))
        plt.plot(range(1, n_epochs+1), epoch_train_sizes, '-o', linewidth=2, markersize=4, color='#2ca02c')
        plt.title('Progression de la taille de l\'ensemble d\'entraînement', fontsize=14, fontweight='bold')
        plt.xlabel('Époque', fontsize=12)
        plt.ylabel('Nombre d\'échantillons', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig('figures/mlp/mlp_training_size.png', dpi=300)
        plt.close()
        print("✅ Graphique de progression de taille sauvegardé")
        
    except Exception as e:
        print(f"Erreur lors de la création des graphiques: {str(e)}")

    # Évaluation finale du meilleur modèle sur l'ensemble de test
    test_pred = best_model.predict(X_test)
    test_accuracy = accuracy_score(y_test, test_pred)
    test_precision = precision_score(y_test, test_pred, zero_division=0)
    test_recall = recall_score(y_test, test_pred, zero_division=0)
    test_f1 = f1_score(y_test, test_pred, zero_division=0)
    conf_matrix = confusion_matrix(y_test, test_pred)

    # Tracer la matrice de confusion pour le meilleur modèle
    try:
        plt.figure(figsize=(8, 6))
        sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='Blues',
                   xticklabels=['Normal', 'Attack'], yticklabels=['Normal', 'Attack'])
        plt.title('Matrice de confusion MLP (Ensemble de test)', fontsize=14, fontweight='bold')
        plt.xlabel('Classe prédite', fontsize=12)
        plt.ylabel('Classe réelle', fontsize=12)
        plt.tight_layout()
        plt.savefig('figures/mlp/mlp_confusion_matrix.png', dpi=300)
        plt.close()
        print("✅ Matrice de confusion sauvegardée")
    except Exception as e:
        print(f"Erreur lors de la création de la matrice de confusion: {str(e)}")

    # **CRITIQUE**: Sauvegarder avec le nom attendu par le système
    try:
        joblib.dump(best_model, "models/mlp_best.pkl")
        print("✅ Meilleur modèle MLP sauvegardé dans models/mlp_best.pkl")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde du modèle: {str(e)}")

    # Afficher les résultats finaux
    print("\n=== Résultats finaux ===")
    print(f"Accuracy sur l'ensemble de test: {test_accuracy:.4f}")
    print(f"Precision sur l'ensemble de test: {test_precision:.4f}")
    print(f"Recall sur l'ensemble de test: {test_recall:.4f}")
    print(f"F1-Score sur l'ensemble de test: {test_f1:.4f}")
    
    # Analyser la matrice de confusion
    tn, fp, fn, tp = conf_matrix.ravel()
    total = tn + fp + fn + tp
    print(f"\nDétail de la matrice de confusion:")
    print(f"  - Vrais Négatifs (TN): {tn} ({tn/total*100:.2f}%)")
    print(f"  - Faux Positifs (FP): {fp} ({fp/total*100:.2f}%)")
    print(f"  - Faux Négatifs (FN): {fn} ({fn/total*100:.2f}%)")
    print(f"  - Vrais Positifs (TP): {tp} ({tp/total*100:.2f}%)")
    print(f"  - Taux de faux positifs: {fp/(fp+tn)*100:.2f}%")
    print(f"  - Taux de faux négatifs: {fn/(fn+tp)*100:.2f}%")

    # Retourner les informations d'apprentissage et le meilleur modèle
    return {
        'model': best_model,
        'train_accuracies': train_accuracies,
        'val_accuracies': val_accuracies,
        'train_losses': train_losses,
        'val_losses': val_losses,
        'train_precisions': train_precisions,
        'val_precisions': val_precisions,
        'train_recalls': train_recalls,
        'val_recalls': val_recalls,
        'train_f1s': train_f1s,
        'val_f1s': val_f1s,
        'epoch_train_sizes': epoch_train_sizes,
        'best_val_accuracy': best_val_acc,
        'test_accuracy': test_accuracy,
        'test_precision': test_precision,
        'test_recall': test_recall,
        'test_f1': test_f1,
        'confusion_matrix': conf_matrix
    }


def main(data_path="UNSW_NB15_training-set.csv", test_size=0.2, val_size=0.15, n_epochs=25, random_state=42):
    """
    Fonction principale qui exécute tout le pipeline MLP
    EXACTEMENT comme dans pasteCode.ipynb
    """
    print("=" * 80)
    print("Pipeline d'analyse et d'entraînement MLP pour la détection d'intrusion réseau")
    print("Basé sur la méthode exacte de pasteCode.ipynb avec entraînement progressif")
    print("=" * 80)
    
    start_time = time.time()
    
    try:
        # Charger et prétraiter les données
        X_train, X_val, X_test, y_train, y_val, y_test, scaler, label_encoders = load_and_preprocess_data(
            filepath=data_path, test_size=test_size, val_size=val_size, random_state=random_state
        )
        
        # Sauvegarder le scaler et les encodeurs (compatibilité avec le système)
        try:
            joblib.dump(scaler, "models/scaler.pkl")
            joblib.dump(label_encoders, "models/label_encoders.pkl")
            print("✅ Scaler et encodeurs sauvegardés dans le dossier 'models/'")
        except Exception as e:
            print(f"⚠️ Erreur lors de la sauvegarde du scaler et des encodeurs: {str(e)}")
        
        # Utiliser les meilleurs hyperparamètres trouvés dans le notebook
        print("\n🔧 Configuration des hyperparamètres:")
        
        # Ces sont les hyperparamètres optimaux trouvés dans votre notebook
        best_params = {
            'activation': 'relu', 
            'alpha': 0.0001, 
            'hidden_layer_sizes': (128, 64), 
            'learning_rate': 'constant', 
            'solver': 'adam'
        }
        print(f"Utilisation des hyperparamètres optimaux: {best_params}")
        
        # Si vous voulez re-optimiser, décommentez ces lignes:
        # print("Optimisation des hyperparamètres...")
        # best_params, val_score = optimize_mlp_hyperparameters(X_train, y_train, X_val, y_val)
        
        # Entraînement progressif (LA MÉTHODE PRÉFÉRÉE DU NOTEBOOK)
        print(f"\n🤖 Entraînement progressif du MLP (méthode du notebook):")
        results = train_mlp_progressive(X_train, y_train, X_val, y_val, X_test, y_test, best_params, n_epochs=n_epochs)
        
        # Affichage du temps total d'exécution
        elapsed_time = time.time() - start_time
        print(f"\nTemps total d'exécution: {elapsed_time:.2f} secondes ({elapsed_time/60:.2f} minutes)")
        
        # Résumé des performances
        print(f"\n📊 Résumé des performances:")
        print(f"  - Accuracy finale sur le test: {results['test_accuracy']:.4f}")
        print(f"  - Precision finale sur le test: {results['test_precision']:.4f}")
        print(f"  - Recall final sur le test: {results['test_recall']:.4f}")
        print(f"  - F1-Score final sur le test: {results['test_f1']:.4f}")
        print(f"  - Meilleure accuracy de validation: {results['best_val_accuracy']:.4f}")
        print(f"  - Hyperparamètres utilisés: {best_params}")
        
        # Information sur la compatibilité
        print(f"\n🎯 SUCCÈS - Modèle MLP compatible créé!")
        print(f"✅ Sauvegardé dans: models/mlp_best.pkl")
        print(f"✅ Features: {X_train.shape[1]} (compatible avec le système)")
        print(f"✅ Méthode: Entraînement progressif (comme dans pasteCode.ipynb)")
        print(f"✅ Visualisations: Générées dans figures/mlp/")
        
        # Émettre un bip de succès
        try:
            winsound.Beep(1000, 500)  # Bip de succès
        except:
            pass
        
        return results
    
    except Exception as e:
        print(f"\n❌ Erreur lors de l'exécution du pipeline: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Point d'entrée du script
    print("🚀 Démarrage du re-entraînement MLP avec la méthode du notebook")
    
    # Vérifier si le fichier de données existe
    data_path = "UNSW_NB15_training-set.csv"
    if not os.path.exists(data_path):
        print(f"⚠️ Le fichier {data_path} n'existe pas. Veuillez spécifier le chemin correct.")
        exit(1)
    
    # Exécuter le pipeline principal avec la méthode du notebook
    results = main(data_path=data_path, n_epochs=25)
    
    if results:
        print("\n🎉 SUCCESS! Re-entraînement MLP terminé avec la méthode du notebook!")
        print("🔄 Le modèle MLP est maintenant compatible et prêt à être utilisé dans votre système.")
        print("📝 Remplacez l'ancien models/mlp_best.pkl - le nouveau est compatible avec 42 features.")
    else:
        print("\n😞 Le re-entraînement a échoué. Vérifiez les erreurs ci-dessus.")
