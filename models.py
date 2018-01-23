import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from passlib.apps import custom_app_context as pwd_context

Base = declarative_base()


# Users table to hold authentication information of each user.
class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    picture = Column(String)
    password_hashed = Column(String)

    # hashes password for security
    def hash_password(self, password):
        self.password_hashed = pwd_context.encrypt(password)

    # used for verifying password
    def verify_password(self, password):
        print 'password entered: %s' % password
        print pwd_context.verify(password, self.password_hashed)
        return pwd_context.verify(password, self.password_hashed)


# Holds details of all of the categories
class Categories(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    category = Column(String, index=True)

    # used to serilize data for returning json file
    @property
    def serialize(self):
        return {
            'category_id': self.id,
            'name': self.category
        }

# tables holds details of all of the items (and what category they belong to)


class Items(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    item = Column(String, index=True)
    description = Column(String)
    category_id = Column(Integer, ForeignKey('categories.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    created = Column(DateTime, default=datetime.datetime.utcnow)
    categories = relationship(Categories)
    users = relationship(Users)

    # used to serilize data for returning json file
    @property
    def serialize(self):

        return {
            'cat_id': self.category_id,
            'id': self.id,
            'title': self.item,
            'description': self.description,
            'date_created': self.created

        }


# create database if doesn't exist, then connects.
engine = create_engine('sqlite:///itemCatalog.db')
Base.metadata.create_all(engine)
