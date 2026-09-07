export type Category = {
  id: number;
  name: string;
  slug: string;
  description: string;
  article_count: number;
};

export type Author = {
  username: string;
  display_name: string;
};

export type Tag = {
  name: string;
  slug: string;
};

export type Engagement = {
  views: number;
  reactions: number;
  shares: number;
};

export type ArticleSummary = {
  id: number;
  title: string;
  subtitle: string;
  excerpt: string;
  slug: string;
  category: {
    id: number;
    name: string;
    slug: string;
  };
  author: Author;
  published_at: string | null;
  updated_at: string;
  attachment_mode: string;
  hero_image_url: string;
  featured_image_caption: string;
  featured_image_credit: string;
  tags: Tag[];
  engagement: Engagement;
};

export type ArticleContributor = {
  username: string;
  display_name: string;
  role: string;
  role_display: string;
};

export type ArticleImageAttachment = {
  id: number;
  image_url: string;
  caption: string;
  alt_text: string;
  credit: string;
};

export type ArticleVideoAttachment = {
  id: number;
  video_url: string;
  caption: string;
  credit: string;
};

export type ArticleDetail = ArticleSummary & {
  content: string;
  featured_image_url: string;
  contributors: ArticleContributor[];
  image_attachments: ArticleImageAttachment[];
  video_attachments: ArticleVideoAttachment[];
};

export type SchoolUpdate = {
  id: number;
  title: string;
  slug: string;
  summary: string;
  details: string;
  image_url: string;
  updated_at: string;
};

export type DigitalPublication = {
  id: number;
  title: string;
  slug: string;
  volume: string;
  issue_number: string;
  publication_date: string;
  description: string;
  cover_image_url: string;
  page_count: number;
  file_size: number;
  pdf_url?: string;
};

export type AboutPage = {
  title: string;
  subtitle: string;
  overview: string;
  history: string;
  mission: string;
  vision: string;
  hero_image_url: string;
  updated_at: string;
};

export type PeopleProfile = {
  id: number;
  name: string;
  image_url: string;
  role_title: string;
  courses_handled: string;
  school_position: string;
  institute_department: string;
  achievements: string;
  additional_information: string;
};

export type PeopleGroup = {
  slug: string;
  title: string;
  profiles: PeopleProfile[];
};

export type HomeResponse = {
  latest_articles: ArticleSummary[];
  school_updates: SchoolUpdate[];
  digital_publications: DigitalPublication[];
};

export type CategoriesResponse = {
  categories: Category[];
};

export type ArticlesResponse = {
  count: number;
  articles: ArticleSummary[];
};

export type ArticleDetailResponse = {
  article: ArticleDetail;
  has_reacted: boolean;
  has_shared: boolean;
};

export type ArticleEngagementActionResponse = {
  recorded: boolean;
  has_reacted?: boolean;
  has_shared?: boolean;
  engagement: Engagement;
};

export type SchoolUpdatesResponse = {
  school_updates: SchoolUpdate[];
};

export type SchoolUpdateDetailResponse = {
  school_update: SchoolUpdate;
};

export type DigitalPublicationsResponse = {
  digital_publications: DigitalPublication[];
};

export type DigitalPublicationDetailResponse = {
  digital_publication: DigitalPublication;
};

export type AboutResponse = {
  about: AboutPage | null;
};

export type PeopleResponse = {
  groups: PeopleGroup[];
};
