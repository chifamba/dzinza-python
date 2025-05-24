import React, { useState, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import Cropper from 'react-easy-crop';
import { Loader2, Upload, Trash } from 'lucide-react';
import { Slider } from '@/components/ui/slider';
import api from '@/api';

interface ProfilePictureUploaderProps {
  personId: string;
  initialImageUrl?: string;
  onImageUpdate: (imageUrl: string) => void;
}

export function ProfilePictureUploader({ 
  personId, 
  initialImageUrl,
  onImageUpdate 
}: ProfilePictureUploaderProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [currentImageUrl, setCurrentImageUrl] = useState(initialImageUrl || '');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const onCropComplete = useCallback((croppedArea: any, croppedAreaPixels: any) => {
    setCroppedAreaPixels(croppedAreaPixels);
  }, []);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.addEventListener('load', () => {
        setImageSrc(reader.result as string);
        setIsDialogOpen(true);
      });
      reader.readAsDataURL(file);
    }
  };

  const handleFileUpload = () => {
    fileInputRef.current?.click();
  };

  const createImage = (url: string): Promise<HTMLImageElement> =>
    new Promise((resolve, reject) => {
      const image = new Image();
      image.addEventListener('load', () => resolve(image));
      image.addEventListener('error', error => reject(error));
      image.src = url;
    });

  const getCroppedImg = async (
    imageSrc: string,
    pixelCrop: any
  ): Promise<Blob> => {
    const image = await createImage(imageSrc);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      throw new Error('No 2d context');
    }

    // Set canvas dimensions to match the cropped area
    canvas.width = pixelCrop.width;
    canvas.height = pixelCrop.height;

    // Draw the cropped image onto the canvas
    ctx.drawImage(
      image,
      pixelCrop.x,
      pixelCrop.y,
      pixelCrop.width,
      pixelCrop.height,
      0,
      0,
      pixelCrop.width,
      pixelCrop.height
    );

    // Convert the canvas to a blob
    return new Promise((resolve, reject) => {
      canvas.toBlob(blob => {
        if (!blob) {
          reject(new Error('Canvas is empty'));
          return;
        }
        resolve(blob);
      }, 'image/jpeg', 0.95);
    });
  };

  const uploadCroppedImage = async () => {
    if (!imageSrc || !croppedAreaPixels) return;

    try {
      setIsUploading(true);
      
      // Get the cropped image as a blob
      const croppedImage = await getCroppedImg(imageSrc, croppedAreaPixels);
      
      // Create a file from the blob
      const file = new File([croppedImage], 'profile-picture.jpg', { type: 'image/jpeg' });
      
      // Upload the file using the API
      const response = await api.uploadProfilePicture(personId, file);
      
      // Update the state with the new image URL
      setCurrentImageUrl(response.imageUrl);
      onImageUpdate(response.imageUrl);
      
      // Close the dialog
      setIsDialogOpen(false);
    } catch (error) {
      console.error('Error uploading image:', error);
    } finally {
      setIsUploading(false);
    }
  };

  const deleteProfilePicture = async () => {
    if (!currentImageUrl || !confirm('Are you sure you want to delete the profile picture?')) {
      return;
    }

    try {
      setIsUploading(true);
      await api.deleteProfilePicture(personId);
      setCurrentImageUrl('');
      onImageUpdate('');
    } catch (error) {
      console.error('Error deleting profile picture:', error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-center">
        <div className="relative h-32 w-32 rounded-full overflow-hidden border-2 border-gray-200">
          {currentImageUrl ? (
            <img
              src={currentImageUrl}
              alt="Profile"
              className="object-cover w-full h-full"
            />
          ) : (
            <div className="w-full h-full bg-gray-100 flex items-center justify-center text-gray-400">
              No Image
            </div>
          )}
        </div>
      </div>

      <div className="flex justify-center space-x-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleFileUpload}
          disabled={isUploading}
        >
          {isUploading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Upload className="mr-2 h-4 w-4" />
          )}
          Upload
        </Button>

        {currentImageUrl && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={deleteProfilePicture}
            disabled={isUploading}
          >
            <Trash className="mr-2 h-4 w-4" />
            Delete
          </Button>
        )}

        <Input
          type="file"
          ref={fileInputRef}
          className="hidden"
          accept="image/*"
          onChange={onFileChange}
        />
      </div>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Crop Profile Picture</DialogTitle>
          </DialogHeader>

          <div className="relative h-[300px] w-full">
            {imageSrc && (
              <Cropper
                image={imageSrc}
                crop={crop}
                zoom={zoom}
                aspect={1}
                onCropChange={setCrop}
                onCropComplete={onCropComplete}
                onZoomChange={setZoom}
              />
            )}
          </div>

          <div className="py-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Zoom</span>
              <span className="text-sm text-gray-500">{zoom.toFixed(1)}x</span>
            </div>
            <Slider
              min={1}
              max={3}
              step={0.1}
              value={[zoom]}
              onValueChange={(value) => setZoom(value[0])}
            />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={uploadCroppedImage} disabled={isUploading}>
              {isUploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
