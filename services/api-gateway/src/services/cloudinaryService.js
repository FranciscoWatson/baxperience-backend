const cloudinary = require('cloudinary').v2;

class CloudinaryService {
  constructor() {
    // Configure Cloudinary
    cloudinary.config({
      cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
      api_key: process.env.CLOUDINARY_API_KEY,
      api_secret: process.env.CLOUDINARY_API_SECRET,
    });
  }

  /**
   * Upload profile image to Cloudinary
   * @param {Buffer} fileBuffer - Image file buffer
   * @param {string} userId - User ID for organizing images
   * @returns {Promise<string>} - Cloudinary URL
   */
  async uploadProfileImage(fileBuffer, userId) {
    return new Promise((resolve, reject) => {
      const uploadStream = cloudinary.uploader.upload_stream(
        {
          folder: 'baxperience/profiles',
          public_id: `user_${userId}_${Date.now()}`,
          transformation: [
            { width: 500, height: 500, crop: 'fill', gravity: 'face' },
            { quality: 'auto' },
            { fetch_format: 'auto' }
          ],
          overwrite: true,
          resource_type: 'image'
        },
        (error, result) => {
          if (error) {
            console.error('Cloudinary upload error:', error);
            reject(error);
          } else {
            resolve(result.secure_url);
          }
        }
      );

      // Write buffer to stream
      uploadStream.end(fileBuffer);
    });
  }

  /**
   * Delete old profile image from Cloudinary
   * @param {string} imageUrl - Cloudinary URL to delete
   */
  async deleteProfileImage(imageUrl) {
    try {
      if (!imageUrl || !imageUrl.includes('cloudinary.com')) {
        return;
      }

      // Extract public_id from URL
      const urlParts = imageUrl.split('/');
      const filename = urlParts[urlParts.length - 1];
      const publicId = `baxperience/profiles/${filename.split('.')[0]}`;

      await cloudinary.uploader.destroy(publicId);
      console.log('Old profile image deleted:', publicId);
    } catch (error) {
      console.error('Error deleting old image:', error);
      // Don't throw error, just log it
    }
  }

  /**
   * Validate image file
   * @param {Object} file - Multer file object
   * @returns {boolean}
   */
  validateImage(file) {
    const allowedMimeTypes = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp'];
    const maxSize = 5 * 1024 * 1024; // 5MB

    if (!allowedMimeTypes.includes(file.mimetype)) {
      throw new Error('Invalid file type. Only JPEG, PNG, and WebP images are allowed.');
    }

    if (file.size > maxSize) {
      throw new Error('File size too large. Maximum size is 5MB.');
    }

    return true;
  }
}

module.exports = new CloudinaryService();
