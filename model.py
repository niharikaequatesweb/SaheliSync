import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import cosine_similarity
import re
from datetime import datetime

class RoommateMatchingModel:
    def __init__(self):
        self.scaler = MinMaxScaler()
        self.label_encoders = {}
        self.feature_cols = []
        self.is_fitted = False
        
    def extract_time_from_text(self, time_str):
        """Extract time from natural language text"""
        if not time_str or pd.isna(time_str):
            return 12  # Default to noon
            
        time_str = str(time_str).lower()
        
        # Look for time patterns
        time_patterns = [
            r'(\d{1,2})\s*(?::|\.)\s*(\d{2})\s*(am|pm)',  # 10:30 PM
            r'(\d{1,2})\s*(am|pm)',  # 10 PM
            r'(\d{1,2})\s*o\'?clock',  # 10 o'clock
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, time_str)
            if match:
                hour = int(match.group(1))
                if len(match.groups()) >= 3 and match.group(3):  # Has AM/PM
                    if match.group(3) == 'pm' and hour != 12:
                        hour += 12
                    elif match.group(3) == 'am' and hour == 12:
                        hour = 0
                return hour
        
        # Handle special cases
        if 'midnight' in time_str or '12 am' in time_str:
            return 0
        elif 'noon' in time_str or '12 pm' in time_str:
            return 12
        elif 'evening' in time_str:
            return 19
        elif 'morning' in time_str:
            return 8
        elif 'night' in time_str:
            return 22
        elif 'afternoon' in time_str:
            return 15
            
        return 12  # Default to noon

    def extract_rating_from_text(self, text):
        """Extract numerical rating from text"""
        if not text or pd.isna(text):
            return 5  # Default middle rating
            
        text = str(text).lower()
        
        # Look for numerical ratings
        rating_match = re.search(r'(\d+)(?:/10|out of 10|\s*(?:rating|score))', text)
        if rating_match:
            return min(int(rating_match.group(1)), 10)
        
        # Handle descriptive ratings
        rating_map = {
            'very high': 9, 'extremely high': 10, 'super high': 9,
            'high': 8, 'quite high': 7,
            'medium': 5, 'moderate': 5, 'average': 5,
            'low': 3, 'quite low': 2, 'very low': 1,
            'none': 1, 'zero': 1
        }
        
        for key, value in rating_map.items():
            if key in text:
                return value
                
        return 5  # Default

    def categorize_text(self, text, categories):
        """Categorize text into predefined categories"""
        if not text or pd.isna(text):
            return categories[0] if categories else 'unknown'
            
        text = str(text).lower()
        
        for category in categories:
            if category.lower() in text:
                return category
                
        return categories[0] if categories else 'unknown'

    def convert_omnidim_to_dataframe(self, profiles_data):
        """Convert Omnidim AI agent data to standardized DataFrame"""
        processed_profiles = []
        
        for profile in profiles_data:
            extracted_vars = profile.get("extracted_variables", {})
            
            # Process each profile
            processed_profile = {
                'user_id': profile.get("call_id", f"user_{len(processed_profiles)}"),
                'user_name': f"User_{len(processed_profiles) + 1}",
                'timestamp': profile.get("timestamp", datetime.now().isoformat()),
                
                # Sleep preferences
                'bedtime_num': self.extract_time_from_text(extracted_vars.get("bedtime")),
                'wake_time_num': self.extract_time_from_text(extracted_vars.get("wake_time")),
                'sleep_type': self.categorize_text(
                    extracted_vars.get("sleep_type"), 
                    ['light', 'heavy', 'normal']
                ),
                
                # Cleanliness
                'cleanliness_rating': self.extract_rating_from_text(extracted_vars.get("cleanliness_rating")),
                'cleanliness_habits': extracted_vars.get("cleanliness_habits", ""),
                
                # Social preferences
                'social_energy_rating': self.extract_rating_from_text(extracted_vars.get("social_energy")),
                'guests_preference': self.categorize_text(
                    extracted_vars.get("guests_preference"),
                    ['never', 'rarely', 'sometimes', 'often', 'frequently']
                ),
                
                # Living preferences
                'room_type_preference': self.categorize_text(
                    extracted_vars.get("room_preference"),
                    ['private', 'shared', 'either']
                ),
                'privacy_importance': self.extract_rating_from_text(extracted_vars.get("privacy_importance")),
                
                # Lifestyle
                'pets': self.categorize_text(
                    extracted_vars.get("pets"),
                    ['none', 'cat', 'dog', 'other', 'multiple']
                ),
                'substances': self.categorize_text(
                    extracted_vars.get("substances"),
                    ['none', 'social', 'regular', 'heavy']
                ),
                'dietary_restrictions': self.categorize_text(
                    extracted_vars.get("dietary"),
                    ['none', 'vegetarian', 'vegan', 'allergies', 'other']
                ),
                'noise_tolerance': self.extract_rating_from_text(extracted_vars.get("noise_tolerance")),
                
                # Summary and sentiment
                'summary': profile.get("summary", ""),
                'sentiment': profile.get("sentiment", "neutral")
            }
            
            processed_profiles.append(processed_profile)
        
        return pd.DataFrame(processed_profiles)

    def prepare_features(self, df):
        """Prepare features for matching algorithm"""
        # Define feature columns
        self.feature_cols = [
            'bedtime_num', 'wake_time_num', 'sleep_type', 'cleanliness_rating',
            'social_energy_rating', 'guests_preference', 'room_type_preference',
            'privacy_importance', 'pets', 'substances', 'dietary_restrictions',
            'noise_tolerance'
        ]
        
        # Encode categorical variables
        categorical_cols = ['sleep_type', 'guests_preference', 'room_type_preference', 
                           'pets', 'substances', 'dietary_restrictions']
        
        for col in categorical_cols:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
            
            # Fit and transform or just transform
            if not self.is_fitted:
                df[col] = self.label_encoders[col].fit_transform(df[col].astype(str))
            else:
                # Handle new categories
                known_classes = set(self.label_encoders[col].classes_)
                new_classes = set(df[col].unique()) - known_classes
                if new_classes:
                    # Add new classes to the encoder
                    all_classes = list(known_classes) + list(new_classes)
                    self.label_encoders[col].classes_ = np.array(all_classes)
                
                df[col] = df[col].apply(lambda x: self.label_encoders[col].transform([str(x)])[0] 
                                       if str(x) in self.label_encoders[col].classes_ else 0)
        
        # Scale numerical features
        numerical_cols = ['bedtime_num', 'wake_time_num', 'cleanliness_rating',
                         'social_energy_rating', 'privacy_importance', 'noise_tolerance']
        
        if not self.is_fitted:
            df[numerical_cols] = self.scaler.fit_transform(df[numerical_cols])
            self.is_fitted = True
        else:
            df[numerical_cols] = self.scaler.transform(df[numerical_cols])
        
        return df[self.feature_cols].values

    def find_matches(self, profiles_data, target_user_id, n_matches=5):
        """Find best matches for a target user"""
        # Convert to DataFrame
        df = self.convert_omnidim_to_dataframe(profiles_data)
        
        if len(df) < 2:
            return {"error": "Need at least 2 profiles for matching"}
        
        # Find target user index
        target_index = None
        for idx, user_id in enumerate(df['user_id']):
            if user_id == target_user_id:
                target_index = idx
                break
        
        if target_index is None:
            return {"error": f"User {target_user_id} not found"}
        
        # Prepare features
        X = self.prepare_features(df.copy())
        
        # Combined similarity model
        knn = NearestNeighbors(n_neighbors=min(n_matches+1, len(X)), metric='euclidean')
        knn.fit(X)
        distances, indices = knn.kneighbors([X[target_index]])
        
        # Cosine similarity
        cosine_sim = cosine_similarity([X[target_index]], X).flatten()
        
        # Combine scores
        knn_scores = 1 - (distances.flatten() / (distances.max() + 1e-8))
        combined_scores = (knn_scores + cosine_sim[indices.flatten()]) / 2
        
        # Scale to 85-95 range
        if len(combined_scores) > 1:
            min_score, max_score = combined_scores.min(), combined_scores.max()
            if max_score > min_score:
                scaled_scores = 85 + 10 * (combined_scores - min_score) / (max_score - min_score)
            else:
                scaled_scores = np.full_like(combined_scores, 90)
        else:
            scaled_scores = np.array([90])
        
        # Create results
        matches = []
        for i, idx in enumerate(indices.flatten()):
            if df.iloc[idx]['user_id'] != target_user_id:  # Exclude self
                match_info = {
                    'user_id': df.iloc[idx]['user_id'],
                    'user_name': df.iloc[idx]['user_name'],
                    'match_score': float(scaled_scores[i]),
                    'compatibility_factors': self.get_compatibility_factors(df, target_index, idx),
                    'profile_summary': df.iloc[idx]['summary']
                }
                matches.append(match_info)
        
        # Sort by match score
        matches = sorted(matches, key=lambda x: x['match_score'], reverse=True)
        
        return {
            'target_user': {
                'user_id': df.iloc[target_index]['user_id'],
                'user_name': df.iloc[target_index]['user_name']
            },
            'matches': matches[:n_matches],
            'total_profiles': len(df)
        }

    def get_compatibility_factors(self, df, user1_idx, user2_idx):
        """Get detailed compatibility analysis between two users"""
        user1 = df.iloc[user1_idx]
        user2 = df.iloc[user2_idx]
        
        factors = {
            'sleep_compatibility': self.calculate_sleep_compatibility(user1, user2),
            'cleanliness_compatibility': abs(user1['cleanliness_rating'] - user2['cleanliness_rating']) <= 2,
            'social_compatibility': abs(user1['social_energy_rating'] - user2['social_energy_rating']) <= 3,
            'lifestyle_compatibility': user1['pets'] == user2['pets'] and user1['substances'] == user2['substances'],
            'privacy_compatibility': abs(user1['privacy_importance'] - user2['privacy_importance']) <= 2
        }
        
        return factors

    def calculate_sleep_compatibility(self, user1, user2):
        """Calculate sleep schedule compatibility"""
        bedtime_diff = abs(user1['bedtime_num'] - user2['bedtime_num'])
        wake_diff = abs(user1['wake_time_num'] - user2['wake_time_num'])
        
        # Handle wrap-around for 24-hour format
        bedtime_diff = min(bedtime_diff, 24 - bedtime_diff)
        wake_diff = min(wake_diff, 24 - wake_diff)
        
        # Compatible if within 2 hours
        return bedtime_diff <= 2 and wake_diff <= 2

# Usage example for Flask app integration
def integrate_with_flask_app(all_profiles, target_user_id):
    """Function to integrate with Flask app"""
    matcher = RoommateMatchingModel()
    results = matcher.find_matches(all_profiles, target_user_id, n_matches=5)
    return results