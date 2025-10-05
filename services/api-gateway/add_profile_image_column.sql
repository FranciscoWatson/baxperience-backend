-- Add profile_image_url column to usuarios table
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS profile_image_url VARCHAR(500);

-- Add comment to the column
COMMENT ON COLUMN usuarios.profile_image_url IS 'Cloudinary URL for user profile image';

-- Optional: Create an index if you plan to query by this column
-- CREATE INDEX idx_usuarios_profile_image ON usuarios(profile_image_url) WHERE profile_image_url IS NOT NULL;
