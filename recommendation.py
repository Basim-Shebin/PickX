from db import execute_query
from ml_module import predict_suitability
from utils import get_semantic_skills

def calculate_recommendation_score(worker_profile, job):
    """
    Calculates a compatibility score between a worker and a job.
    Uses semantic matching to relate terms like 'electrician' and 'electrical'.
    """
    score = 0
    
    # 1. Mandatory Rule: Semantic Skill Match
    if worker_profile.get('skills') and job.get('skill_required'):
        worker_skills = [s.strip().lower() for s in worker_profile['skills'].split(',')]
        job_skill = job['skill_required'].lower()
        
        # Check for direct match
        if job_skill in worker_skills:
            score += 40
        else:
            # Check for semantic match
            semantic_variants = get_semantic_skills(job_skill)
            if any(s in worker_skills for s in semantic_variants):
                score += 35  # Slightly lower score for semantic match
            else:
                return 0  # Still no match
    else:
        return 0
            
    # 2. Rule: Location Match (City)
    # Note: job has location_city, user has city
    # We need to fetch the user city if not in profile, but app.py passes it usually
    if worker_profile.get('city') == job.get('location_city'):
        score += 20
        
    # 3. Rule: Area Proximity
    if worker_profile.get('area') == job.get('location_area'):
        score += 10
        
    # 4. Intelligence: ML Suitability Score (0-30 points weight)
    ml_score = predict_suitability(worker_profile)
    score += (ml_score * 0.3)
    
    return min(score, 100)

def get_recommended_workers(job_id):
    """
    Returns a list of recommended workers for a specific job.
    """
    job = execute_query("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
    if not job:
        return []
    job = job[0]
    
    # Fetch all available workers
    workers = execute_query("""
        SELECT u.user_id, u.full_name, u.city, u.area, wp.* 
        FROM users u 
        JOIN worker_profiles wp ON u.user_id = wp.worker_id 
        WHERE u.role = 'worker' AND wp.availability_status = 'available'
    """)
    
    scored_workers = []
    for worker in workers:
        score = calculate_recommendation_score(worker, job)
        if score > 0:
            worker['match_score'] = round(score, 1)
            scored_workers.append(worker)
            
    # Sort by score descending
    return sorted(scored_workers, key=lambda x: x['match_score'], reverse=True)
