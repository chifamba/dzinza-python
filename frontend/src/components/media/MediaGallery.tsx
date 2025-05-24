import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Upload, Loader2, Trash, FileText, Image, FileIcon } from 'lucide-react';
import api from '@/api';
import { useAuth } from '@/contexts/AuthContext';

interface MediaItem {
  id: string;
  filename: string;
  fileType: string;
  fileSize: number;
  url: string;
  uploadDate: string;
  description?: string;
  tags?: string[];
}

interface MediaGalleryProps {
  personId: string;
}

export function MediaGallery({ personId }: MediaGalleryProps) {
  const { user } = useAuth();
  const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [selectedMedia, setSelectedMedia] = useState<MediaItem | null>(null);
  const [fileToUpload, setFileToUpload] = useState<File | null>(null);
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'images' | 'documents'>('all');

  const fetchMediaItems = async () => {
    setLoading(true);
    try {
      const response = await api.getPersonMedia(personId);
      setMediaItems(response.items || []);
    } catch (error) {
      console.error('Failed to fetch media items:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMediaItems();
  }, [personId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFileToUpload(e.target.files[0]);
    }
  };

  const uploadFile = async () => {
    if (!fileToUpload) return;

    setLoading(true);
    try {
      await api.uploadPersonMedia(personId, fileToUpload, {
        description,
        tags: tags.split(',').map(tag => tag.trim()).filter(Boolean)
      });
      await fetchMediaItems();
      setUploadDialogOpen(false);
      resetUploadForm();
    } catch (error) {
      console.error('Failed to upload file:', error);
    } finally {
      setLoading(false);
    }
  };

  const deleteMedia = async (mediaId: string) => {
    if (!confirm('Are you sure you want to delete this media item?')) {
      return;
    }

    setLoading(true);
    try {
      await api.deletePersonMedia(personId, mediaId);
      await fetchMediaItems();
      if (viewDialogOpen && selectedMedia?.id === mediaId) {
        setViewDialogOpen(false);
      }
    } catch (error) {
      console.error('Failed to delete media item:', error);
    } finally {
      setLoading(false);
    }
  };

  const resetUploadForm = () => {
    setFileToUpload(null);
    setDescription('');
    setTags('');
  };

  const openMediaViewer = (media: MediaItem) => {
    setSelectedMedia(media);
    setViewDialogOpen(true);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getFileTypeIcon = (fileType: string) => {
    if (fileType.startsWith('image/')) return <Image className="h-6 w-6" />;
    if (fileType.startsWith('text/') || fileType.includes('document')) return <FileText className="h-6 w-6" />;
    return <FileIcon className="h-6 w-6" />;
  };

  const filteredMediaItems = mediaItems.filter(item => {
    if (activeTab === 'all') return true;
    if (activeTab === 'images') return item.fileType.startsWith('image/');
    if (activeTab === 'documents') return !item.fileType.startsWith('image/');
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Media Gallery</h2>
        <Button onClick={() => setUploadDialogOpen(true)}>
          <Upload className="mr-2 h-4 w-4" />
          Upload
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="images">Images</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
        </TabsList>
        <TabsContent value="all">
          <MediaGridView 
            mediaItems={filteredMediaItems}
            loading={loading}
            onView={openMediaViewer}
            onDelete={deleteMedia}
          />
        </TabsContent>
        <TabsContent value="images">
          <MediaGridView 
            mediaItems={filteredMediaItems}
            loading={loading}
            onView={openMediaViewer}
            onDelete={deleteMedia}
          />
        </TabsContent>
        <TabsContent value="documents">
          <MediaGridView 
            mediaItems={filteredMediaItems}
            loading={loading}
            onView={openMediaViewer}
            onDelete={deleteMedia}
          />
        </TabsContent>
      </Tabs>

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Upload Media</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="file">File</Label>
              <Input id="file" type="file" onChange={handleFileChange} />
              {fileToUpload && (
                <p className="text-sm text-muted-foreground">
                  Selected: {fileToUpload.name} ({formatFileSize(fileToUpload.size)})
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description (Optional)</Label>
              <Input
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Add a description..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tags">Tags (Optional, comma separated)</Label>
              <Input
                id="tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="e.g. certificate, document, memorial"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUploadDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={uploadFile} 
              disabled={!fileToUpload || loading}
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Upload
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Media Viewer Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="sm:max-w-[800px]">
          {selectedMedia && (
            <>
              <DialogHeader>
                <DialogTitle>{selectedMedia.filename}</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                {selectedMedia.fileType.startsWith('image/') ? (
                  <div className="flex justify-center">
                    <img
                      src={selectedMedia.url}
                      alt={selectedMedia.filename}
                      className="max-h-[400px] object-contain"
                    />
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-8">
                    {getFileTypeIcon(selectedMedia.fileType)}
                    <p className="mt-2 text-muted-foreground">
                      {selectedMedia.fileType}
                    </p>
                    <Button 
                      className="mt-4" 
                      onClick={() => window.open(selectedMedia.url, '_blank')}
                    >
                      Open File
                    </Button>
                  </div>
                )}
                <div className="space-y-2">
                  <h3 className="text-sm font-medium">Details</h3>
                  <p className="text-sm text-muted-foreground">
                    Uploaded: {new Date(selectedMedia.uploadDate).toLocaleDateString()}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Size: {formatFileSize(selectedMedia.fileSize)}
                  </p>
                  {selectedMedia.description && (
                    <p className="text-sm mt-2">
                      {selectedMedia.description}
                    </p>
                  )}
                  {selectedMedia.tags && selectedMedia.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {selectedMedia.tags.map(tag => (
                        <span 
                          key={tag} 
                          className="px-2 py-1 bg-primary-100 text-primary-800 rounded-full text-xs"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => window.open(selectedMedia.url, '_blank')}
                >
                  Download
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => deleteMedia(selectedMedia.id)}
                >
                  <Trash className="mr-2 h-4 w-4" />
                  Delete
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface MediaGridViewProps {
  mediaItems: MediaItem[];
  loading: boolean;
  onView: (media: MediaItem) => void;
  onDelete: (mediaId: string) => void;
}

function MediaGridView({ mediaItems, loading, onView, onDelete }: MediaGridViewProps) {
  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (mediaItems.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">No media items found</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mt-4">
      {mediaItems.map((media) => (
        <div
          key={media.id}
          className="border rounded-md overflow-hidden flex flex-col"
        >
          <div 
            className="h-32 flex items-center justify-center cursor-pointer"
            onClick={() => onView(media)}
          >
            {media.fileType.startsWith('image/') ? (
              <img
                src={media.url}
                alt={media.filename}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full w-full bg-gray-100">
                {media.fileType.startsWith('text/') || media.fileType.includes('document') ? (
                  <FileText className="h-12 w-12 text-gray-500" />
                ) : (
                  <FileIcon className="h-12 w-12 text-gray-500" />
                )}
              </div>
            )}
          </div>
          <div className="p-2 bg-white flex-grow">
            <p className="text-sm font-medium truncate" title={media.filename}>
              {media.filename}
            </p>
            <div className="flex justify-between items-center mt-1">
              <span className="text-xs text-muted-foreground">
                {new Date(media.uploadDate).toLocaleDateString()}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(media.id);
                }}
              >
                <Trash className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
