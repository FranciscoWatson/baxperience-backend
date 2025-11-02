const cloudinaryService = require('../../src/services/cloudinaryService');
const cloudinary = require('cloudinary').v2;

jest.mock('cloudinary');

describe('CloudinaryService', () => {
  let mockUploadStream;
  let mockUploader;

  beforeEach(() => {
    jest.clearAllMocks();

    mockUploadStream = {
      end: jest.fn()
    };

    mockUploader = {
      upload_stream: jest.fn((options, callback) => {
        // Simulate async upload
        setTimeout(() => {
          callback(null, {
            secure_url: 'https://res.cloudinary.com/test/image/upload/v123/test.jpg',
            public_id: 'baxperience/profiles/user_123'
          });
        }, 0);
        return mockUploadStream;
      }),
      destroy: jest.fn().mockResolvedValue({ result: 'ok' })
    };

    cloudinary.uploader = mockUploader;
    cloudinary.config = jest.fn();
  });

  describe('uploadProfileImage', () => {
    it('should upload image successfully', async () => {
      const fileBuffer = Buffer.from('fake-image-data');
      const userId = '123';

      const result = await cloudinaryService.uploadProfileImage(fileBuffer, userId);

      expect(result).toBe('https://res.cloudinary.com/test/image/upload/v123/test.jpg');
      expect(mockUploader.upload_stream).toHaveBeenCalled();
      expect(mockUploadStream.end).toHaveBeenCalledWith(fileBuffer);
    });

    it('should use correct upload options', async () => {
      const fileBuffer = Buffer.from('fake-image-data');
      const userId = '456';

      await cloudinaryService.uploadProfileImage(fileBuffer, userId);

      const uploadOptions = mockUploader.upload_stream.mock.calls[0][0];
      
      expect(uploadOptions.folder).toBe('baxperience/profiles');
      expect(uploadOptions.public_id).toContain('user_456');
      expect(uploadOptions.overwrite).toBe(true);
      expect(uploadOptions.resource_type).toBe('image');
    });

    it('should apply correct transformations', async () => {
      const fileBuffer = Buffer.from('fake-image-data');
      const userId = '789';

      await cloudinaryService.uploadProfileImage(fileBuffer, userId);

      const uploadOptions = mockUploader.upload_stream.mock.calls[0][0];
      
      expect(uploadOptions.transformation).toBeDefined();
      expect(uploadOptions.transformation).toHaveLength(3);
      expect(uploadOptions.transformation[0]).toMatchObject({
        width: 500,
        height: 500,
        crop: 'fill',
        gravity: 'face'
      });
    });

    it('should reject on upload error', async () => {
      mockUploader.upload_stream.mockImplementation((options, callback) => {
        setTimeout(() => {
          callback(new Error('Upload failed'), null);
        }, 0);
        return mockUploadStream;
      });

      const fileBuffer = Buffer.from('fake-image-data');

      await expect(
        cloudinaryService.uploadProfileImage(fileBuffer, '123')
      ).rejects.toThrow('Upload failed');
    });

    it('should generate unique public_id for each upload', async () => {
      const fileBuffer = Buffer.from('fake-image-data');
      
      await cloudinaryService.uploadProfileImage(fileBuffer, '123');
      const publicId1 = mockUploader.upload_stream.mock.calls[0][0].public_id;
      
      // Wait a bit to ensure different timestamp
      await new Promise(resolve => setTimeout(resolve, 10));
      
      await cloudinaryService.uploadProfileImage(fileBuffer, '123');
      const publicId2 = mockUploader.upload_stream.mock.calls[1][0].public_id;
      
      expect(publicId1).not.toBe(publicId2);
    });

    it('should handle large file buffers', async () => {
      const largeBuffer = Buffer.alloc(1024 * 1024 * 4); // 4MB
      
      const result = await cloudinaryService.uploadProfileImage(largeBuffer, '123');

      expect(result).toBeDefined();
      expect(mockUploadStream.end).toHaveBeenCalledWith(largeBuffer);
    });
  });

  describe('deleteProfileImage', () => {
    it('should delete image successfully', async () => {
      const imageUrl = 'https://res.cloudinary.com/test/image/upload/v123/baxperience/profiles/user_123.jpg';

      await cloudinaryService.deleteProfileImage(imageUrl);

      expect(mockUploader.destroy).toHaveBeenCalledWith(
        'baxperience/profiles/user_123'
      );
    });

    it('should handle non-cloudinary URLs', async () => {
      const imageUrl = 'https://example.com/image.jpg';

      await cloudinaryService.deleteProfileImage(imageUrl);

      expect(mockUploader.destroy).not.toHaveBeenCalled();
    });

    it('should handle null URL', async () => {
      await cloudinaryService.deleteProfileImage(null);

      expect(mockUploader.destroy).not.toHaveBeenCalled();
    });

    it('should handle undefined URL', async () => {
      await cloudinaryService.deleteProfileImage(undefined);

      expect(mockUploader.destroy).not.toHaveBeenCalled();
    });

    it('should handle empty string URL', async () => {
      await cloudinaryService.deleteProfileImage('');

      expect(mockUploader.destroy).not.toHaveBeenCalled();
    });

    it('should not throw on delete error', async () => {
      mockUploader.destroy.mockRejectedValue(new Error('Delete failed'));
      
      const imageUrl = 'https://res.cloudinary.com/test/image/upload/v123/baxperience/profiles/user_123.jpg';

      await expect(
        cloudinaryService.deleteProfileImage(imageUrl)
      ).resolves.not.toThrow();
    });

    it('should extract correct public_id from complex URL', async () => {
      const imageUrl = 'https://res.cloudinary.com/mycloud/image/upload/v1234567890/baxperience/profiles/user_999_1234567890.jpg';

      await cloudinaryService.deleteProfileImage(imageUrl);

      expect(mockUploader.destroy).toHaveBeenCalledWith(
        'baxperience/profiles/user_999_1234567890'
      );
    });

    it('should handle URLs with query parameters', async () => {
      const imageUrl = 'https://res.cloudinary.com/test/image/upload/v123/baxperience/profiles/user_123.jpg?version=2';

      await cloudinaryService.deleteProfileImage(imageUrl);

      expect(mockUploader.destroy).toHaveBeenCalled();
    });
  });

  describe('validateImage', () => {
    it('should validate valid JPEG image', () => {
      const file = {
        mimetype: 'image/jpeg',
        size: 1024 * 1024 * 2 // 2MB
      };

      const result = cloudinaryService.validateImage(file);

      expect(result).toBe(true);
    });

    it('should validate valid PNG image', () => {
      const file = {
        mimetype: 'image/png',
        size: 1024 * 1024 * 3
      };

      const result = cloudinaryService.validateImage(file);

      expect(result).toBe(true);
    });

    it('should validate valid WebP image', () => {
      const file = {
        mimetype: 'image/webp',
        size: 1024 * 1024
      };

      const result = cloudinaryService.validateImage(file);

      expect(result).toBe(true);
    });

    it('should reject invalid mime type', () => {
      const file = {
        mimetype: 'application/pdf',
        size: 1024 * 1024
      };

      expect(() => {
        cloudinaryService.validateImage(file);
      }).toThrow('Invalid file type');
    });

    it('should reject file that is too large', () => {
      const file = {
        mimetype: 'image/jpeg',
        size: 1024 * 1024 * 10 // 10MB - exceeds 5MB limit
      };

      expect(() => {
        cloudinaryService.validateImage(file);
      }).toThrow('File size too large');
    });

    it('should reject unsupported image formats', () => {
      const unsupportedFormats = [
        'image/gif',
        'image/bmp',
        'image/svg+xml',
        'image/tiff'
      ];

      unsupportedFormats.forEach(mimetype => {
        const file = { mimetype, size: 1024 * 1024 };
        
        expect(() => {
          cloudinaryService.validateImage(file);
        }).toThrow('Invalid file type');
      });
    });

    it('should accept file at exactly 5MB limit', () => {
      const file = {
        mimetype: 'image/jpeg',
        size: 5 * 1024 * 1024 // Exactly 5MB
      };

      const result = cloudinaryService.validateImage(file);

      expect(result).toBe(true);
    });

    it('should reject file just over 5MB limit', () => {
      const file = {
        mimetype: 'image/jpeg',
        size: (5 * 1024 * 1024) + 1 // Just over 5MB
      };

      expect(() => {
        cloudinaryService.validateImage(file);
      }).toThrow('File size too large');
    });

    it('should accept very small files', () => {
      const file = {
        mimetype: 'image/png',
        size: 100 // 100 bytes
      };

      const result = cloudinaryService.validateImage(file);

      expect(result).toBe(true);
    });

    it('should handle case variations in mime type', () => {
      const file = {
        mimetype: 'image/JPEG',
        size: 1024 * 1024
      };

      // Current implementation is case-sensitive
      expect(() => {
        cloudinaryService.validateImage(file);
      }).toThrow('Invalid file type');
    });
  });

  describe('Edge cases', () => {
    it('should handle concurrent uploads', async () => {
      const fileBuffer = Buffer.from('fake-image-data');
      
      const promises = [
        cloudinaryService.uploadProfileImage(fileBuffer, '1'),
        cloudinaryService.uploadProfileImage(fileBuffer, '2'),
        cloudinaryService.uploadProfileImage(fileBuffer, '3')
      ];

      const results = await Promise.all(promises);

      expect(results).toHaveLength(3);
      expect(mockUploader.upload_stream).toHaveBeenCalledTimes(3);
    });

    it('should handle empty buffer', async () => {
      const emptyBuffer = Buffer.alloc(0);

      const result = await cloudinaryService.uploadProfileImage(emptyBuffer, '123');

      expect(result).toBeDefined();
    });

    it('should handle special characters in userId', async () => {
      const fileBuffer = Buffer.from('fake-image-data');
      const userId = 'user@123-test_id';

      const result = await cloudinaryService.uploadProfileImage(fileBuffer, userId);

      expect(result).toBeDefined();
      expect(result).toBeDefined();
    });
  });
});
