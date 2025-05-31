// Default profile images from Pexels featuring African people
export const defaultImages = {
  olderMale: 'https://images.pexels.com/photos/3831612/pexels-photo-3831612.jpeg',
  olderFemale: 'https://images.pexels.com/photos/3876407/pexels-photo-3876407.jpeg',
  adultMale: 'https://images.pexels.com/photos/2182970/pexels-photo-2182970.jpeg',
  adultFemale: 'https://images.pexels.com/photos/3310695/pexels-photo-3310695.jpeg',
  boy: 'https://images.pexels.com/photos/1139613/pexels-photo-1139613.jpeg',
  girl: 'https://images.pexels.com/photos/1068205/pexels-photo-1068205.jpeg',
};

export type PersonCategory = 'olderMale' | 'olderFemale' | 'adultMale' | 'adultFemale' | 'boy' | 'girl';

export const getDefaultImage = (category: PersonCategory): string => {
  return defaultImages[category];
};