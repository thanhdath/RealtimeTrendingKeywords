dic_big_topics = {'thoi-su':'thoi-su',
                'the-gioi':'thoi-su',
                'giai-tri':'giai-tri',
                'the-thao':'the-thao',
                'phap-luat':'phap-luat',
                'giao-duc':'giao-duc',
                'suc-khoe':'y-te',
                'doi-song':'doi-song',
                'du-lich':'du-lich',
                'khoa-hoc':'khoa-hoc-cong-nghe',
                'so-hoa':'khoa-hoc-cong-nghe',
                'xe':'xe',
                'tam-su':'doi-song',
                'hai':'giai-tri',
                'y-kien':'doi-song',
                'goc-nhin':'goc-nhin',
                'kinh-doanh':'kinh-te',
                'thi-truong-chung-khoan':'kinh-te',
                'bat-dong-san':'kinh-te',
                'doanh-nghiep':'kinh-te',
                'tai-chinh-ngan-hang':'kinh-te',
                'tai-chinh-quoc-te':'kinh-te',
                'vi-mo-dau-tu':'kinh-te',
                'song':'doi-song',
                'thi-truong':'kinh-te'}

def get_big_topics(topic):
    return dic_big_topics[topic]